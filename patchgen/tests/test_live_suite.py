"""Actual model rate must not count deterministic passes or missing artifacts."""
import json
from pathlib import Path
import tempfile
import unittest
from patchgen.live_suite import collect


class LiveSuiteTests(unittest.TestCase):
    def test_analysis_refuses_incomplete_or_deterministic_runs(self):
        from patchgen.live_analysis import analyze
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';root.mkdir()
            for status,mode in [('running','live_model'),('completed','deterministic_authored_suite')]:
                (root/'summary.json').write_text(json.dumps({'status':status,'mode':mode,'results':[]}))
                with self.assertRaises(ValueError):analyze(root,Path(tmp)/'analysis')
                self.assertFalse((Path(tmp)/'analysis').exists())

    def test_locked_configuration_is_exact_and_refuses_overrides(self):
        from argparse import Namespace
        from patchgen.live_suite import LOCKED_CONFIG, execute, resolve_configuration
        args=dict(locked=True,backend=None,model=None,strategy=None)
        self.assertEqual(resolve_configuration(Namespace(**args)),LOCKED_CONFIG)
        for key,value in [('backend','ollama'),('model','ministral-3:8b'),('strategy','candidate_edits')]:
            with self.assertRaises(ValueError):resolve_configuration(Namespace(**{**args,key:value}))
        unlocked=resolve_configuration(Namespace(locked=False,backend=None,model=None,strategy=None))
        self.assertEqual(unlocked,dict(backend='ollama',model='ministral-3:8b',strategy='candidate_edits'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                execute(Path(tmp)/'out','ministral-3:8b','candidate_edits',locked=True)
            self.assertFalse((Path(tmp)/'out').exists())

    def test_missing_report_is_failed_not_a_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=collect(Path(tmp),1,3)
            self.assertFalse(result['generated_patch_validated'])
            self.assertEqual(result['model_requests'],0)

    def test_deterministic_pass_never_counts_as_model_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'run').mkdir();(root/'review').mkdir()
            (root/'review/index.html').write_text('review')
            (root/'run/report.json').write_text(json.dumps({'status':'validation_passed','proposal_report':{'mode':'deterministic_proposal'}}))
            self.assertFalse(collect(root,0,1)['generated_patch_validated'])

    def test_failed_contract_retains_actual_requests_and_generation_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=root/'run/proposal/requests/01';request.mkdir(parents=True)
            (request/'request.json').write_text('{}')
            (request/'request-measurement.json').write_text(json.dumps({'elapsed_seconds':2.5,'memory_samples':[{'models':[]}]}))
            (request/'edit-validation.json').write_text(json.dumps({'status':'failed','error':'bad site id'}))
            (root/'run/report.json').write_text(json.dumps({'status':'failed','proposal_report':{'mode':'live_model','error':'contract rejected'}}))
            result=collect(root,1,3)
            self.assertEqual(result['model_requests'],1)
            self.assertEqual(result['generation_seconds'],2.5)
            self.assertEqual(result['requests'][0]['edit_validation']['error'],'bad site id')
            self.assertNotIn('memory_samples',result['requests'][0]['measurement'])
            self.assertFalse(result['generated_patch_validated'])
