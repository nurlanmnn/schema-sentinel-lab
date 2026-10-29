"""Adversarial checks for structured edits; no reference migration answers used."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from patchgen.generator import ContractError, edit_prompt, resolve_edits, unified_diff, generate, resolve_file, resolve_lines
from test_generator import CASE


def value(edits=None, outcome='patch'):
    return dict(outcome=outcome,edits=[] if edits is None else edits,
                rationale='Test rationale',confidence=.7,assumptions=[])


class EditTests(unittest.TestCase):
    def test_exact_deletion_and_replacement(self):
        original='keep\nremove\nlast\n'
        edits=[dict(before='remove\n',after=''),dict(before='last',after='updated')]
        self.assertEqual(resolve_edits(original,value(edits)),'keep\nupdated\n')

    def test_reject_missing_ambiguous_overlapping_and_noop_anchors(self):
        cases=[('same same',[dict(before='same',after='other')]),
               ('abc',[dict(before='missing',after='')]),
               ('abc',[dict(before='ab',after='x'),dict(before='bc',after='y')]),
               ('abc',[dict(before='a',after='a')]),
               ('aaa',[dict(before='aa',after='x')])]
        for source,edits in cases:
            with self.subTest(source=source,edits=edits),self.assertRaises(ContractError):
                resolve_edits(source,value(edits))

    def test_original_anchors_not_newly_inserted_text(self):
        self.assertEqual(resolve_edits('abc',value([dict(before='a',after='b'),dict(before='b',after='x')])),'bxc')

    def test_no_change_and_clarification_never_contain_edits(self):
        for outcome in ('no_change','needs_clarification'):
            self.assertEqual(resolve_edits('abc',value(outcome=outcome)),'abc')
            with self.assertRaises(ContractError): resolve_edits('abc',value([dict(before='a',after='x')],outcome))
        with self.assertRaises(ContractError): resolve_edits('abc',value())

    def test_one_file_prompt_excludes_other_files_and_reference_metadata(self):
        case=copy.deepcopy(CASE)
        case['reference_answer']='SECRET_ANSWER'
        case['change']['reference_answer']='SECRET_ANSWER'
        for file in case['affected_files']:
            file['reference_answer']='SECRET_ANSWER'
            file['positions'][0]['reference_answer']='SECRET_ANSWER'
        encoded=json.dumps(edit_prompt(case,case['affected_files'][0]))
        self.assertNotIn('SECRET_ANSWER',encoded)
        payload=json.loads(edit_prompt(case,case['affected_files'][0])[1]['content'])
        self.assertEqual(len(payload['affected_files']),1)
        self.assertEqual(payload['affected_files'][0]['path'],'runtimes/python/main.py')
        self.assertNotIn('reference/',encoded)

    def test_diff_handles_missing_final_newline_and_applies_exactly(self):
        for old,new in [('one\nlast','one\nupdated'),('one\nlast','one\nlast\n'),('one\n','')]:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                subprocess.run(['git','init',str(root)],check=True,capture_output=True)
                file=root/'sample.txt';file.write_text(old)
                diff=root/'change.patch';diff.write_text(unified_diff('sample.txt',old,new))
                result=subprocess.run(['git','apply',str(diff)],cwd=root,text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(file.read_text(),new)

    def test_rejected_file_stops_assembly_without_retry_or_partial_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_api(endpoint,route,data=None):
                return {'models':[{'name':'ministral-3:3b'}]} if route=='/api/tags' else {}
            with patch('patchgen.generator.api',side_effect=fake_api),patch('patchgen.generator.request_model',return_value=value([dict(before='not in source',after='')])) as request:
                with self.assertRaisesRegex(ContractError,'file proposal rejected'):
                    generate(CASE,'ministral-3:3b','http://127.0.0.1:11434',Path(tmp),strategy='exact_edits')
                self.assertEqual(request.call_count,len(CASE['affected_files']))
                self.assertFalse((Path(tmp)/'workspace').exists())
                self.assertFalse((Path(tmp)/'assembly.json').exists())

    def test_clarification_in_one_file_prevents_a_partial_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_api(endpoint,route,data=None):
                return {'models':[{'name':'ministral-3:3b'}]} if route=='/api/tags' else {}
            responses=[value(outcome='no_change') for _ in CASE['affected_files']]
            responses[-1]=value(outcome='needs_clarification')
            pending=iter(responses)
            def fake_request(messages,model,endpoint,directory):
                directory.mkdir(parents=True)
                return next(pending)
            with patch('patchgen.generator.api',side_effect=fake_api),patch('patchgen.generator.request_model',side_effect=fake_request):
                result=generate(CASE,'ministral-3:3b','http://127.0.0.1:11434',Path(tmp),strategy='exact_edits')
                self.assertEqual(result['outcome'],'needs_clarification')
                self.assertEqual(result['diff'],'')



class IndependentOracleTests(unittest.TestCase):
    def test_weakened_evidence_validator_is_rejected(self):
        from patchgen.oracle import check_evidence_rejections
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            directory=root/'testbed/tests';directory.mkdir(parents=True)
            (directory/'e2e_test.py').write_text('CASES = '+repr([{'entity_id':'normal'},{'entity_id':''},{'entity_id':'雪'},{'entity_id':'quoted \"\n\\'}])+'\ndef validate_evidence(*args):\n    pass\n')
            with self.assertRaisesRegex(AssertionError,'accepted invalid intermediate identifier'):
                check_evidence_rejections(root,lambda **fields: fields)


class FileContentTests(unittest.TestCase):
    def test_file_outcomes_reject_empty_or_unchanged_patches(self):
        response=value(); del response['edits'];response['updated_source']='updated'
        self.assertEqual(resolve_file('original',response),'updated')
        for invalid in ['', 'original']:
            response['updated_source']=invalid
            with self.assertRaises(ContractError): resolve_file('original',response)
        for outcome in ('no_change','needs_clarification'):
            response['outcome']=outcome;response['updated_source']=''
            self.assertEqual(resolve_file('original',response),'original')
            response['updated_source']='unexpected edit'
            with self.assertRaises(ContractError): resolve_file('original',response)

    def test_file_prompt_excludes_reference_metadata(self):
        case=copy.deepcopy(CASE);case['reference']='SECRET_ANSWER'
        case['affected_files'][0]['positions'][0]['reference']='SECRET_ANSWER'
        messages=edit_prompt(case,case['affected_files'][0],strategy='file_content')
        self.assertNotIn('SECRET_ANSWER',json.dumps(messages))
        payload=json.loads(messages[-1]['content'])
        self.assertEqual(payload['prompt_version'],'2.1')
        self.assertIn('updated_source',payload['response_schema']['required'])
        self.assertEqual(len(payload['affected_files']),1)


class LineEditTests(unittest.TestCase):
    def test_original_line_numbers_allow_adjacent_edits_and_deletions(self):
        response=value([dict(start_line=1,end_line=1,replacement_lines=['updated']),
                        dict(start_line=2,end_line=3,replacement_lines=[])])
        self.assertEqual(resolve_lines('one\ntwo\nthree\nlast',response),'updated\nlast')

    def test_overlaps_out_of_bounds_noninteger_and_partial_lines_fail(self):
        edits=[dict(start_line=0,end_line=1,replacement_lines=[]),
               dict(start_line=2,end_line=1,replacement_lines=[]),
               dict(start_line=1,end_line=4,replacement_lines=[]),
               dict(start_line=True,end_line=1,replacement_lines=[]),
               dict(start_line=1,end_line=1,replacement_lines=['embedded\nline'])]
        for edit in edits:
            with self.subTest(edit=edit),self.assertRaises(ContractError):
                resolve_lines('one\ntwo\n',value([edit]))
        with self.assertRaisesRegex(ContractError,'overlapping'):
            resolve_lines('one\ntwo\n',value([dict(start_line=1,end_line=2,replacement_lines=[]),dict(start_line=2,end_line=2,replacement_lines=[])]))

    def test_line_prompt_has_exact_source_and_no_test_guidance_for_runtime(self):
        file=CASE['affected_files'][0]
        messages=edit_prompt(CASE,file,strategy='line_edits')
        payload=json.loads(messages[-1]['content']);context=payload['affected_files'][0]
        self.assertEqual([l['text'] for l in context['source_lines']],file['source_context'].splitlines())
        self.assertEqual([l['line'] for l in context['source_lines']],list(range(1,len(file['source_context'].splitlines())+1)))
        self.assertEqual(payload['prompt_version'],'2.3')
        self.assertNotIn('This is test code',messages[0]['content'])
        test_prompt=edit_prompt(CASE,CASE['affected_files'][-1],strategy='line_edits')
        self.assertIn('This is test code',test_prompt[0]['content'])

    def test_line_outcomes_never_apply_partial_changes(self):
        for outcome in ('no_change','needs_clarification'):
            self.assertEqual(resolve_lines('source',value(outcome=outcome)),'source')
            with self.assertRaises(ContractError):
                resolve_lines('source',value([dict(start_line=1,end_line=1,replacement_lines=['updated'])],outcome))


class ImpactCoverageTests(unittest.TestCase):
    def test_missing_sites_and_unrelated_ranges_fail(self):
        positions=[dict(start_line=2,end_line=2),dict(start_line=4,end_line=4)]
        with self.assertRaisesRegex(ContractError,'unaddressed'):
            resolve_lines('1\n2\n3\n4\n',value([dict(start_line=2,end_line=2,replacement_lines=['two'])]),positions)
        with self.assertRaisesRegex(ContractError,'does not touch'):
            resolve_lines('1\n2\n3\n4\n',value([dict(start_line=1,end_line=1,replacement_lines=[]),dict(start_line=2,end_line=2,replacement_lines=['two']),dict(start_line=4,end_line=4,replacement_lines=['four'])]),positions)

    def test_range_may_include_branch_context_around_an_impact(self):
        positions=[dict(start_line=2,end_line=2)]
        self.assertEqual(resolve_lines('branch\nremoved\nkeep\n',value([dict(start_line=1,end_line=2,replacement_lines=[])]),positions),'keep\n')


if __name__=='__main__': unittest.main()
