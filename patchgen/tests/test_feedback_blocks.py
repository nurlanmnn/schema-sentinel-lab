"""Feedback is scoped to a rejected live attempt and the exact original files."""
import json
from pathlib import Path
import tempfile
import unittest
from patchgen.feedback_blocks import make_prompt, validate_feedback
from patchgen.feedback_probe import build_feedback, execute
from patchgen.generator import ContractError


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.file=dict(path='runtimes/python/main.py',language='python',source_context='old = 1\n',
            positions=[dict(start_line=1,end_line=1,reason='candidate')])
        self.case=dict(contract_version='1.0',source_revision='a'*40,intended_behavior='migration',
            change=dict(id='change',category='field_renamed',old_schema='old',new_schema='new',schema_path='proto/a.proto'),
            affected_files=[self.file])
        self.feedback=dict(source_revision='a'*40,change_id='change',reference_answer='never include',
            files={self.file['path']:dict(previous_response={'outcome':'patch'},validation_diagnostics=['old property does not exist'],
                                        reference_answer='never include either')})

    def test_feedback_identity_and_file_scope_cannot_drift(self):
        for change in (dict(source_revision='b'*40),dict(change_id='wrong'),dict(files={})):
            with self.assertRaises(ContractError):validate_feedback(self.case,{**self.feedback,**change})

    def test_prompt_uses_original_source_and_only_diagnostics_for_this_file(self):
        self.case['model_feedback']=self.feedback
        messages,_=make_prompt(self.case,self.file)
        payload=json.loads(messages[1]['content'])
        self.assertEqual(payload['file']['source_context'],'old = 1\n')
        self.assertEqual(payload['previous_attempt']['validation_diagnostics'],['old property does not exist'])
        self.assertNotIn('never include',json.dumps(messages))
        self.assertEqual(payload['prompt_version'],'2.9-feedback')

    def test_builder_retains_actual_rejection_and_does_not_read_reference_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=root/'requests/01';request.mkdir(parents=True)
            (root/'report.json').write_text(json.dumps(dict(status='failed',error='old property does not exist')))
            (request/'parsed-response.json').write_text(json.dumps({'outcome':'patch'}))
            (request/'edit-validation.json').write_text(json.dumps({'status':'passed'}))
            (root/'reference-response.json').write_text('invalid json, must never read')
            result=build_feedback(root,self.case)
            self.assertEqual(result['files'][self.file['path']]['validation_diagnostics'],['old property does not exist'])
            (root/'report.json').write_text(json.dumps(dict(status='validation_passed')))
            with self.assertRaises(ValueError):build_feedback(root,self.case)

    def test_probe_cannot_exceed_fixed_attempt_bound(self):
        for limit in (0,3,100):
            with self.assertRaises(ValueError):execute(Path('/missing'),Path('/missing-output'),limit)
