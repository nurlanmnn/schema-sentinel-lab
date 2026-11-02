"""Keep diagnostic reporting honest when serving evidence is partial."""
import json
from pathlib import Path
import tempfile
import unittest
from patchgen.live_analysis import analyze, failure_evidence, request_details
from patchgen.live_suite import CASES


class DiagnosticTests(unittest.TestCase):
    def test_completed_analysis_keeps_rejections_and_fixed_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';root.mkdir()
            records=[]
            for case in CASES:
                proposal=root/case/'run/proposal';proposal.mkdir(parents=True)
                (proposal/'model.json').write_text(json.dumps({'tag':{'digest':'fixed-model'}}))
                records.append(dict(case=case,generated_patch_validated=False,model_requests=1,
                    requests=[dict(request='01',edit_validation=dict(status='failed',error='bad review'))],
                    generation_seconds=1,workflow_seconds=2,status='failed'))
            summary=dict(status='completed',mode='live_model',model='local-test',options={},prompt_version='test',results=records)
            (root/'summary.json').write_text(json.dumps(summary))
            result=analyze(root,Path(tmp)/'analysis')
            self.assertEqual(result['validation_rate'],0)
            self.assertEqual(result['planned_cases'],6)
            self.assertEqual({r['outcome'] for r in result['rows']},{'file_contract_or_generation_rejected'})
            self.assertIn('bad review',(Path(tmp)/'analysis/analysis.md').read_text())
            summary['results'].append(records[0])
            (root/'summary.json').write_text(json.dumps(summary))
            with self.assertRaises(ValueError):analyze(root,Path(tmp)/'duplicate-analysis')

    def test_timing_separates_loading_and_decode_and_ignores_nested_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            nested=root/'workspace/old/requests/01';nested.mkdir(parents=True)
            (nested/'parsed-response.json').write_text('{broken archived data')
            request=root/'requests/01';request.mkdir(parents=True)
            (request/'parsed-response.json').write_text(json.dumps({'confidence':0.99,'outcome':'patch'}))
            result=request_details(root,[{'request':'01','edit_validation':{'status':'failed','error':'missing site'},
                'serving_counts':{'load_duration':2_000_000_000,'eval_duration':4_000_000_000,'eval_count':40}}])
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['load_seconds'],2)
            self.assertEqual(result[0]['output_tokens_per_second'],10)
            self.assertEqual(result[0]['contract_status'],'failed')
            self.assertEqual(result[0]['confidence'],0.99)
            self.assertIsNone(result[0]['prompt_eval_seconds'])

    def test_missing_or_zero_counters_do_not_invent_speed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=request_details(Path(tmp),[{'request':'01','serving_counts':{'eval_count':4,'eval_duration':0}}])
            self.assertIsNone(result[0]['output_tokens_per_second'])
            self.assertIsNone(result[0]['load_seconds'])

    def test_compiler_and_oracle_failures_retain_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'validation.log').write_text('Installing package\nmain.ts(82,5): error TS1128: bad statement.\nmain.ts(82,5): error TS1128: bad statement.\n')
            oracle=root/'telemetry';oracle.mkdir()
            (oracle/'report.json').write_text(json.dumps({'status':'failed','error':'wire mismatch'}))
            evidence=failure_evidence(root)
            self.assertEqual(evidence['compiler_diagnostics'],['main.ts(82,5): error TS1128: bad statement.'])
            self.assertEqual(evidence['telemetry']['error'],'wire mismatch')
