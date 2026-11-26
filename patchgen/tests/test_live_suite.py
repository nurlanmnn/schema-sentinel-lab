"""Actual model rate must not count deterministic passes or missing artifacts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
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
        from patchgen.live_suite import LOCKED_CONFIG, LOCKED_DECISION, execute, resolve_configuration
        args=dict(locked=True,backend=None,model=None,strategy=None)
        self.assertEqual(LOCKED_DECISION,'0045')
        self.assertEqual(LOCKED_CONFIG,dict(backend='selfhosted',model='inkling-2-mini-q8_0',strategy='candidate_semantic_blocks'))
        self.assertEqual(resolve_configuration(Namespace(**args)),LOCKED_CONFIG)
        for key,value in [('backend','ollama'),('model','ministral-3:8b'),('strategy','candidate_edits'), *LOCKED_CONFIG.items()]:
            with self.assertRaises(ValueError):resolve_configuration(Namespace(**{**args,key:value}))
        unlocked=resolve_configuration(Namespace(locked=False,backend=None,model=None,strategy=None))
        self.assertEqual(unlocked,dict(backend='ollama',model='ministral-3:8b',strategy='candidate_edits'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                execute(Path(tmp)/'out','ministral-3:8b','candidate_edits',locked=True)
            self.assertFalse((Path(tmp)/'out').exists())

    def test_locked_cli_selects_0045_and_refuses_overrides(self):
        from patchgen import live_suite
        args=['live_suite','--output','unused','--locked']
        with mock.patch('sys.argv',args), mock.patch.object(live_suite,'execute',return_value=0) as execute:
            self.assertEqual(live_suite.main(),0)
            self.assertEqual(execute.call_args.args[1:],('inkling-2-mini-q8_0','candidate_semantic_blocks'))
            self.assertEqual(execute.call_args.kwargs['backend'],'selfhosted')
            self.assertTrue(execute.call_args.kwargs['locked'])
        for key,value in live_suite.LOCKED_CONFIG.items():
            with self.subTest(option=key), mock.patch('sys.argv',args+['--'+key,value]), \
                 mock.patch.object(live_suite,'execute') as execute, mock.patch('sys.stderr'):
                self.assertEqual(live_suite.main(),1)
                execute.assert_not_called()

    def test_missing_report_is_failed_not_a_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=collect(Path(tmp),1,3)
            self.assertFalse(result['generated_patch_validated'])
            self.assertEqual(result['model_requests'],0)
            self.assertEqual(result['failure_category'],'harness')

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

    def test_zero_request_infrastructure_failure_takes_priority_over_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp)/'run/proposal/requests/01'
            request.mkdir(parents=True)
            (request/'request-measurement.json').write_text(json.dumps(
                dict(failure_stage='tls_error', status='failed')))
            result = collect(Path(tmp), 1, 1)
            self.assertEqual(result['model_requests'], 0)
            self.assertEqual(result['failure_category'], 'infrastructure')

    def test_zero_request_live_report_is_a_harness_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'run').mkdir()
            (root/'review').mkdir()
            (root/'review/index.html').write_text('synthetic review')
            (root/'run/report.json').write_text(json.dumps(dict(
                status='validation_passed', proposal_report=dict(mode='live_model'))))
            result = collect(root, 0, 1)
            self.assertFalse(result['generated_patch_validated'])
            self.assertEqual(result['failure_category'], 'harness')
