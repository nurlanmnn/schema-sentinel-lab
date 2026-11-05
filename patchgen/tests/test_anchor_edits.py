"""Exact model blocks cannot bypass the existing candidate coverage gate."""
import json
import unittest
from patchgen.anchor_edits import candidates, make_prompt, resolve
from patchgen.generator import ContractError


class AnchorTests(unittest.TestCase):
    def setUp(self):
        self.source='def f():\n    old = 1\n    return old\n'
        self.positions=[dict(start_line=2,end_line=2,reason='candidate'),dict(start_line=3,end_line=3,reason='candidate')]
        self.file=dict(path='runtimes/python/main.py',language='python',source_context=self.source,positions=self.positions)
        self.inventory=candidates(self.file)
        self.response=dict(outcome='patch',confidence=0.5,rationale='proposal',assumptions=[],
            edits=[dict(before='    old = 1\n    return old\n',after='    new = 1\n    return new\n')],
            candidate_reviews={key:dict(decision='edit',reason='changed use') for key in self.inventory})

    def test_semantic_variant_keeps_block_inventory_and_answer_exclusion(self):
        case = dict(contract_version='1.0', source_revision='a'*40,
                    change=dict(id='rename', category='renaming', schema_path='proto/test.proto', old_schema='old', new_schema='new'),
                    intended_behavior='Rename', affected_files=[self.file], reference_answer='FORBIDDEN_ORACLE')
        old, old_inventory = make_prompt(case, self.file)
        revised, revised_inventory = make_prompt(case, self.file, semantic=True)
        self.assertEqual(old_inventory, revised_inventory)
        self.assertNotIn('FORBIDDEN_ORACLE', json.dumps(revised))
        self.assertEqual(json.loads(revised[1]['content'])['prompt_version'], '3.1-semantic-blocks')
        self.assertIn('before and after are identical', revised[0]['content'])

    def test_exact_blocks_are_host_resolved_and_all_candidates_required(self):
        self.assertEqual(resolve(self.source,self.response,self.inventory,self.positions),
                         'def f():\n    new = 1\n    return new\n')
        self.response['candidate_reviews'].pop('C002')
        with self.assertRaisesRegex(ContractError,'exactly the supplied'):resolve(self.source,self.response,self.inventory,self.positions)

    def test_unknown_and_unaffected_candidates_cannot_be_edited(self):
        for reviews in ({'wrong':dict(decision='edit',reason='test')},
                        list(self.response['candidate_reviews'].values())):
            with self.assertRaises(ContractError):resolve(self.source,{**self.response,'candidate_reviews':reviews},self.inventory,self.positions)
        self.response['candidate_reviews']['C001']['decision']='unaffected'
        with self.assertRaisesRegex(ContractError,'coverage mismatch'):resolve(self.source,self.response,self.inventory,self.positions)

    def test_partial_line_and_ambiguous_and_overlapping_blocks_rejected(self):
        for edits in ([dict(before='old',after='new\n')],
                      [dict(before='    old = 1',after='    new = 1\n')],
                      self.response['edits']+[dict(before='    return old\n',after='    return new\n')]):
            with self.assertRaises(ContractError):resolve(self.source,{**self.response,'edits':edits},self.inventory,self.positions)

    def test_prompt_excludes_reference_answers_and_line_numbers(self):
        case=dict(contract_version='1.0',source_revision='a'*40,intended_behavior='specified migration',
            change=dict(id='test',category='field_renamed',old_schema='old',new_schema='new',schema_path='proto/a.proto'),
            affected_files=[self.file],reference_response='secret expected patch')
        messages,inventory=make_prompt(case,self.file)
        payload=json.loads(messages[1]['content'])
        self.assertNotIn('secret expected patch',json.dumps(messages))
        self.assertEqual(payload['candidates'],[dict(id='C001',source_line='    old = 1\n'),dict(id='C002',source_line='    return old\n')])
        self.assertNotIn('line',payload['candidates'][0])
        self.assertEqual(payload['response_schema']['properties']['candidate_reviews']['required'],['C001','C002'])
        self.assertEqual(inventory,self.inventory)
