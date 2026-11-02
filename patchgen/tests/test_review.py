"""Evidence integrity and human-decision gates using synthetic temporary runs."""
import copy
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from patchgen.review import export, verify, sha
from patchgen.generator import ContractError


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.run=self.root/'run';(self.run/'proposal').mkdir(parents=True)
        self.bundle=self.root/'review'
        self.case=dict(source_revision='a'*40,change=dict(id='synthetic-review'),intended_behavior='Preserve values.')
        self.report=dict(source_revision='a'*40,status='validation_passed',mode='deterministic_proposal',strategy='test-only')
        self.write_run()

    def write_run(self):
        (self.run/'input.json').write_text(json.dumps(self.case))
        (self.run/'report.json').write_text(json.dumps(self.report))
        (self.run/'proposal/report.json').write_text(json.dumps(self.report))
        (self.run/'proposal/validated.patch').write_text('--- a/example\n+++ b/example\n-old\n+new\n')

    def decision(self, decision='approve'):
        raw=(self.bundle/'manifest.json').read_bytes()
        record=dict(decision_version='1.0',manifest_sha256=sha(raw),source_revision='a'*40,change_id='synthetic-review',
                    decision=decision,reviewer='SYNTHETIC TEST',rationale='Test fixture only; no real human approval.',
                    reviewed_complete_bundle=True,recorded_at='2026-11-02T00:00:00Z')
        path=self.root/'synthetic-decision.json';path.write_text(json.dumps(record));return path

    def test_portable_export_and_synthetic_decision(self):
        manifest=export(self.run,self.bundle)
        self.assertTrue(manifest['approval_eligible'])
        self.assertEqual(verify(self.bundle,self.decision())['status'],'verified')
        self.assertTrue((self.bundle/'review.js').is_file())
        self.assertIn('No decision recorded.',(self.bundle/'index.html').read_text())

    def test_changed_patch_rejected(self):
        export(self.run,self.bundle);decision=self.decision()
        (self.bundle/'artifacts/proposal/validated.patch').write_text('tampered')
        with self.assertRaisesRegex(ContractError,'artifact changed'):verify(self.bundle,decision)

    def test_changed_manifest_rejected(self):
        export(self.run,self.bundle);decision=self.decision()
        with (self.bundle/'manifest.json').open('a') as f:f.write(' ')
        with self.assertRaisesRegex(ContractError,'manifest identity'):verify(self.bundle,decision)

    def test_failed_proposal_allows_rejection_only(self):
        self.report['status']='failed';self.write_run()
        manifest=export(self.run,self.bundle)
        self.assertFalse(manifest['approval_eligible'])
        self.assertEqual(verify(self.bundle,self.decision('reject'))['decision'],'reject')
        with self.assertRaisesRegex(ContractError,'approval requires'):verify(self.bundle,self.decision())

    def test_cannot_override_failed_report_eligibility(self):
        self.report['status']='failed';self.write_run();export(self.run,self.bundle)
        path=self.bundle/'manifest.json';manifest=json.loads(path.read_text());manifest['approval_eligible']=True;path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ContractError,'approval requires'):verify(self.bundle,self.decision())

    def test_missing_complete_patch_rejected(self):
        (self.run/'proposal/validated.patch').unlink()
        with self.assertRaisesRegex(ContractError,'complete validated patch'):export(self.run,self.bundle)

    def test_no_overwriting_or_nested_output(self):
        export(self.run,self.bundle)
        with self.assertRaises(FileExistsError):export(self.run,self.bundle)
        with self.assertRaises(ContractError):export(self.run,self.run/'review')

    def test_injected_content_is_data(self):
        self.case['intended_behavior']='</script><img src=x onerror=alert(1)> {{DIFF}}'
        self.write_run()
        (self.run/'proposal/validated.patch').write_text('+<script>alert(2)</script>\n')
        export(self.run,self.bundle)
        page=(self.bundle/'index.html').read_text()
        self.assertNotIn('<img src=x',page)
        self.assertNotIn('<script>alert(2)',page)
        self.assertIn('&lt;script&gt;alert(2)',page)
        self.assertIn('{{DIFF}}',page)

    def test_traversal_and_symlink_rejected(self):
        outside=self.root/'outside';outside.write_text('private')
        (self.run/'measurement.json').symlink_to(outside)
        with self.assertRaisesRegex(ContractError,'escapes bundle'):export(self.run,self.bundle)

    def test_required_acknowledgement_and_reason(self):
        export(self.run,self.bundle);path=self.decision();record=json.loads(path.read_text())
        record['reviewed_complete_bundle']=False;path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ContractError,'acknowledgement'):verify(self.bundle,path)
        record['reviewed_complete_bundle']=True;record['rationale']='  ';path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ContractError,'rationale'):verify(self.bundle,path)

    def test_stale_report_revision_rejected(self):
        self.report['source_revision']='b'*40;self.write_run()
        with self.assertRaisesRegex(ContractError,'revision mismatch'):export(self.run,self.bundle)

    def test_blocked_analysis_can_only_be_rejected(self):
        shutil.rmtree(self.run/'proposal')
        (self.run/'input.json').rename(self.run/'request.json')
        self.report.update(status='rejected',mode='analysis_rejected',strategy='not_run',validation='not_run')
        (self.run/'report.json').write_text(json.dumps(self.report))
        manifest=export(self.run,self.bundle)
        self.assertFalse(manifest['approval_eligible'])
        self.assertEqual(manifest['input_artifact'],'request.json')
        self.assertEqual(manifest['report_artifact'],'report.json')
        self.assertEqual(verify(self.bundle,self.decision('reject'))['decision'],'reject')
        with self.assertRaisesRegex(ContractError,'approval requires'):
            verify(self.bundle,self.decision())

    def test_no_proposal_cannot_claim_validation_passed(self):
        shutil.rmtree(self.run/'proposal')
        with self.assertRaisesRegex(ContractError,'rejected analysis'):
            export(self.run,self.bundle)
