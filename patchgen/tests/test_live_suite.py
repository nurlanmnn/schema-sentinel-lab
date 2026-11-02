"""Actual model rate must not count deterministic passes or missing artifacts."""
import json
from pathlib import Path
import tempfile
import unittest
from patchgen.live_suite import collect


class LiveSuiteTests(unittest.TestCase):
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
