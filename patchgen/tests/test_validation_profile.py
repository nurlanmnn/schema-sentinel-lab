"""Independent tests are opt-in evaluator inputs, never model-editable source."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from patchgen.generator import ContractError, check_patch, edit_prompt, load_validation_profile
from test_generator import ROOT

CASE=json.loads((ROOT/'patchgen/fixtures/entity-name-removal/runtime-input.json').read_text())


class ValidationProfileTests(unittest.TestCase):
    def test_profile_is_pinned_and_only_migrates_test_files(self):
        profile,diff=load_validation_profile(CASE,'entity-name-removal')
        self.assertFalse(profile['model_editable'])
        self.assertEqual(profile['source_revision'],CASE['source_revision'])
        self.assertEqual(diff.count('diff --git '),2)
        self.assertNotIn('diff --git a/runtimes/',diff)
        self.assertNotIn('diff --git a/generated/',diff)

    def test_changed_source_schema_or_test_patch_is_rejected(self):
        for mutate in ('revision','schema'):
            case=copy.deepcopy(CASE)
            if mutate=='revision':case['source_revision']='a'*40
            else:case['change']['new_schema']+='\n'
            with self.subTest(mutate=mutate),self.assertRaises(ContractError):
                load_validation_profile(case,'entity-name-removal')
        original=Path.read_text
        def changed(file,*args,**kwargs):
            result=original(file,*args,**kwargs)
            return result+'\n' if file.name=='validation-tests.patch' else result
        with patch.object(Path,'read_text',changed),self.assertRaises(ContractError):
            load_validation_profile(CASE,'entity-name-removal')

    def test_model_prompts_do_not_contain_test_sources_or_profile_answers(self):
        for file in CASE['affected_files']:
            payload=json.loads(edit_prompt(CASE,file,'line_edits')[-1]['content'])
            self.assertEqual(len(payload['affected_files']),1)
            self.assertTrue(payload['affected_files'][0]['path'].startswith('runtimes/'))
            encoded=json.dumps(payload)
            self.assertNotIn('validation-tests.patch',encoded)
            self.assertNotIn('test_evidence.py',encoded)
            self.assertNotIn('expected.patch',encoded)

    def test_model_cannot_edit_evaluator_owned_tests(self):
        _,diff=load_validation_profile(CASE,'entity-name-removal')
        with self.assertRaisesRegex(ContractError,'not allowed'):
            check_patch(diff,CASE)
        expanded=copy.deepcopy(CASE)
        expanded['affected_files'].append({'path':'testbed/tests/e2e_test.py'})
        with self.assertRaisesRegex(ContractError,'runtime-only'):
            load_validation_profile(expanded,'entity-name-removal')


if __name__=='__main__':unittest.main()
