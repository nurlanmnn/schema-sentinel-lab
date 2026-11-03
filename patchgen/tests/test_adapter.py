import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from patchgen.adapter import adapt,coverage
from patchgen.generator import ContractError,edit_prompt

ROOT=Path(__file__).resolve().parents[2]
DETECTOR=json.loads((ROOT/'patchgen/fixtures/adapter/detector.json').read_text())
LOCATOR=json.loads((ROOT/'patchgen/fixtures/adapter/locator.json').read_text())
CASE=json.loads((ROOT/'patchgen/fixtures/entity-name-rename/runtime-input.json').read_text())


class AdapterTests(unittest.TestCase):
    def invoke(self,detector=None,locator=None):
        sources={f['path']:f['source_context'] for f in CASE['affected_files']}
        with patch('patchgen.adapter.command',side_effect=lambda args,repo:sources[args[-1].split(':',1)[1]]),patch('patchgen.adapter.verify_source'):
            return adapt(ROOT,detector or DETECTOR,locator or LOCATOR)

    def test_fixture_roundtrip_and_reference_coverage(self):
        case,provenance=self.invoke()
        self.assertEqual(case,CASE)
        self.assertIn('not live',provenance['locator_producer'])
        expected=json.loads((ROOT/'patchgen/reference/entity-name-rename/expected.json').read_text())
        self.assertEqual(coverage(expected,LOCATOR)['recall'],1)
        reduced=copy.deepcopy(LOCATOR);reduced['files'][0]['positions'].pop()
        self.assertLess(coverage(expected,reduced)['recall'],1)

    def test_stale_missing_ambiguous_and_unsafe_inputs_rejected(self):
        mutations=[lambda d,l:l.update(source_revision='0'*40),lambda d,l:l.update(change_id='wrong'),
          lambda d,l:l.update(adapter_version='2'),lambda d,l:d.update(status='ambiguous'),
          lambda d,l:l.update(status='partial'),lambda d,l:d['change'].update(category='unknown'),
          lambda d,l:l['files'][0].update(source_sha256='bad'),lambda d,l:l.update(files=[]),
          lambda d,l:l['files'][0].update(path='../escape.py'),lambda d,l:l['files'][0].update(language='csharp'),
          lambda d,l:l['files'][0]['positions'][0].update(resolution='uncertain'),
          lambda d,l:l['files'][0]['positions'].append(l['files'][0]['positions'][0]),
          lambda d,l:l['files'][0]['positions'][0].update(start_line=True),lambda d,l:l.pop('old_schema_sha256'),
          lambda d,l:d.pop('intended_behavior'),
          lambda d,l:l['files'][0]['positions'][0].update(required_reference=True,binding_evidence=[{}])]
        for mutate in mutations:
            d=copy.deepcopy(DETECTOR);l=copy.deepcopy(LOCATOR);mutate(d,l)
            with self.subTest(mutate=mutate),self.assertRaises((ContractError,KeyError)):self.invoke(d,l)

    def test_provenance_and_reference_not_in_model_prompt(self):
        case,_=self.invoke();case['answer']='SECRET';case['producer']='SECRET'
        self.assertNotIn('SECRET',json.dumps(edit_prompt(case,case['affected_files'][0],'migration_edits')))

    def test_general_migration_prompt_retains_removal_replay(self):
        old=edit_prompt(CASE,CASE['affected_files'][0],'line_edits')
        new=edit_prompt(CASE,CASE['affected_files'][0],'migration_edits')
        self.assertIn('Do not invent a new field',old[0]['content'])
        self.assertIn('renames migrate',new[0]['content'])
        self.assertNotIn('Do not invent a new field',new[0]['content'])


if __name__=='__main__':unittest.main()
