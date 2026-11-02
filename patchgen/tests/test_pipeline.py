"""Independent structural mutations and syntax snippets, separate from producer rules."""
import copy
import json
import unittest
from pathlib import Path
from google.protobuf.descriptor_pb2 import FileDescriptorProto
from patchgen.detector import compare, detect
from patchgen.locator import scan, locate
from patchgen.adapter import adapt, coverage
from patchgen.generator import ContractError, resolve_candidates, edit_prompt

ROOT = Path(__file__).resolve().parents[2]


class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.old = FileDescriptorProto(name='model.proto',package='simulation.v1',syntax='proto3')
        m = self.old.message_type.add(name='Entity')
        m.field.add(name='display_name',number=2,type=9,label=1)
        self.new = copy.deepcopy(self.old)

    def test_wire_identity_rename(self):
        self.new.message_type[0].field[0].name='caption'
        events, errors=compare(self.old,self.new)
        self.assertEqual([e['category'] for e in events],['field_renamed'])
        self.assertEqual(events[0]['message'],'simulation.v1.Entity')
        self.assertFalse(errors)

    def test_type_change(self):
        self.new.message_type[0].field[0].type=12
        self.assertEqual(compare(self.old,self.new)[0][0]['category'],'field_type_changed')

    def test_removal(self):
        del self.new.message_type[0].field[:]
        self.assertEqual(compare(self.old,self.new)[0][0]['category'],'field_removed')

    def test_nested_message(self):
        nested=self.old.message_type[0].nested_type.add(name='Position')
        nested.field.add(name='x',number=1,type=2,label=1)
        self.new.CopyFrom(self.old)
        self.new.message_type[0].nested_type[0].field[0].type=1
        self.assertEqual(compare(self.old,self.new)[0][0]['message'],'simulation.v1.Entity.Position')

    def test_enum_addition(self):
        self.old.enum_type.add(name='State').value.add(name='UNKNOWN',number=0)
        self.new.CopyFrom(self.old)
        self.new.enum_type[0].value.add(name='ACTIVE',number=1)
        self.assertEqual(compare(self.old,self.new)[0][0]['category'],'enum_value_added')

    def test_enum_value_metadata_not_silently_accepted(self):
        self.old.enum_type.add(name='State').value.add(name='UNKNOWN',number=0)
        self.new.CopyFrom(self.old)
        self.new.enum_type[0].value[0].options.deprecated=True
        self.assertTrue(compare(self.old,self.new)[1])

    def test_identity_mismatch_rejected(self):
        for key,value in [('name','other.proto'),('package','simulation.v2')]:
            changed=copy.deepcopy(self.old);setattr(changed,key,value)
            self.assertTrue(compare(self.old,changed)[1])
            self.assertFalse(compare(self.old,changed)[0])

    def test_unsupported_cardinality_and_addition(self):
        self.new.message_type[0].field[0].label=3
        self.assertTrue(compare(self.old,self.new)[1])
        self.new.CopyFrom(self.old)
        self.new.message_type[0].field.add(name='id',number=1,type=9,label=1)
        self.assertTrue(compare(self.old,self.new)[1])

    def test_multiple_events_not_exportable(self):
        schema='syntax="proto3"; package test; message Entity { string name=1; }'
        result=detect(schema,schema.replace('string name','bytes caption'),'entity.proto','a'*40,'multi','UTF-8')
        self.assertEqual(result['status'],'partial')
        self.assertEqual(len(result['events']),2)

    def test_comment_only_semantics_not_claimed(self):
        schema='syntax="proto3"; package test; message Entity { string name=1; }'
        result=detect('// meters\n'+schema,'// feet\n'+schema,'entity.proto','a'*40,'units','')
        self.assertEqual(result['status'],'partial')

    def test_file_metadata_is_not_silently_accepted(self):
        self.new.message_type[0].field[0].name='caption'
        self.new.options.java_package='different'
        self.assertTrue(compare(self.old,self.new)[1])

    def test_json_name_only_is_unsupported(self):
        self.new.message_type[0].field[0].json_name='somethingElse'
        self.assertTrue(compare(self.old,self.new)[1])



class LocatorTests(unittest.TestCase):
    def test_reads_writes_construction_casts_naming(self):
        samples={
            'python':('x = Entity(display_name="a")\nx.display_name = y.display_name\n# x.display_name\n', {1,2}),
            'typescript':('const x = { displayName: "a" };\nconst y = (x as Entity).displayName;\n// x.displayName\n', {1,2}),
            'csharp':('class Test { void M() {\nvar x = new Entity { DisplayName = "a" };\nvar y = x.DisplayName;\n// x.DisplayName\n} }', {2,3})}
        for language,(source,expected) in samples.items():
            with self.subTest(language=language):
                positions,warnings,error=scan(source,language,'display_name')
                self.assertEqual({p['start_line'] for p in positions},expected)
                self.assertFalse(error)

    def test_literal_and_dynamic_reflection(self):
        positions,warnings,error=scan('getattr(e, "name")\ngetattr(e, field)\n','python','name')
        self.assertEqual([p['start_line'] for p in positions],[1])
        self.assertEqual(warnings[0]['line'],2)

    def test_parse_failure(self):
        self.assertTrue(scan('const x = (','typescript','name')[2])


class PinnedIntegrationTests(unittest.TestCase):
    def test_three_real_schema_pairs_and_runtime_inventories(self):
        import tempfile
        import subprocess
        revision='26304c1ed2f4738676a9607e8fe21e17ebd090f0'
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source'
            subprocess.run(['git','worktree','add','--detach',str(source),revision],cwd=ROOT,check=True,capture_output=True)
            try:
                for name in ('entity-name-removal','entity-name-rename','v2-identifier-bytes'):
                    with self.subTest(case=name):
                        fixture=json.loads((ROOT/'patchgen/fixtures'/name/'runtime-input.json').read_text())
                        change=fixture['change']
                        record=detect(change['old_schema'],change['new_schema'],change['schema_path'],revision,change['id'],fixture['intended_behavior'])
                        self.assertEqual(record['status'],'complete')
                        self.assertEqual(record['change']['category'],change['category'])
                        located=locate(source,record)
                        adapted,provenance=adapt(source,record,located)
                        truth=json.loads((ROOT/'patchgen/reference'/name/'expected.json').read_text())
                        if 'positions' in truth['runtime_sites'][0]:
                            truth['runtime_sites']=[dict(path=f['path'],lines=[p['start_line'] for p in f['positions']]) for f in truth['runtime_sites']]
                        measured=coverage(truth,located)
                        self.assertEqual(measured['matched_sites'],6)
                        self.assertEqual(len(measured['extra']),3 if name=='v2-identifier-bytes' else 0)
                        self.assertEqual(len(adapted['affected_files']),3)
            finally:
                subprocess.run(['git','worktree','remove','--force',str(source)],cwd=ROOT,check=True,capture_output=True)


class CandidateTests(unittest.TestCase):
    def test_unaffected_candidate_is_preserved(self):
        source='old.name\nother.name\n'
        value=dict(outcome='patch',edits=[dict(start_line=1,end_line=1,replacement_lines=['old.caption'])],
                   rationale='rename',confidence=.5,assumptions=[],candidate_reviews=[
                       dict(line=1,decision='edit',reason='changed type'),dict(line=2,decision='unaffected',reason='different version')])
        positions=[dict(start_line=i,end_line=i) for i in (1,2)]
        self.assertEqual(resolve_candidates(source,value,positions),'old.caption\nother.name\n')
        value['candidate_reviews'].pop()
        with self.assertRaises(ContractError):resolve_candidates(source,value,positions)

    def test_cannot_edit_unaffected_candidate(self):
        value=dict(outcome='patch',edits=[dict(start_line=1,end_line=2,replacement_lines=['changed'])],
                   rationale='rename',confidence=.5,assumptions=[],candidate_reviews=[
                       dict(line=1,decision='edit',reason='changed'),dict(line=2,decision='unaffected',reason='other')])
        with self.assertRaises(ContractError):
            resolve_candidates('a\nb\n',value,[dict(start_line=1,end_line=2)])

    def test_malformed_candidate_edit_has_contract_error(self):
        value=dict(outcome='patch',edits=[dict(start_line='bad',end_line=2,replacement_lines=['changed'])],
                   rationale='rename',confidence=.5,assumptions=[],candidate_reviews=[])
        with self.assertRaises(ContractError):
            resolve_candidates('a\nb\n',value,[dict(start_line=1,end_line=2)])

    def test_prompt_version_and_no_answer_leak(self):
        case=json.loads((ROOT/'patchgen/fixtures/entity-name-rename/runtime-input.json').read_text())
        case['reference_answer']='SECRET_REFERENCE'
        messages=edit_prompt(case,case['affected_files'][0],'candidate_edits')
        self.assertNotIn('SECRET_REFERENCE',json.dumps(messages))
        self.assertEqual(json.loads(messages[1]['content'])['prompt_version'],'2.5')


class RenameTokenTests(unittest.TestCase):
    def test_all_three_languages_preserve_structure(self):
        from patchgen.rename_tokens import make_prompt, resolve
        case=json.loads((ROOT/'patchgen/fixtures/entity-name-rename/runtime-input.json').read_text())
        for file in case['affected_files']:
            with self.subTest(language=file['language']):
                prompt,tokens=make_prompt(case,file)
                edits=[]
                for token in tokens:
                    replacement=token['allowed'][0]
                    if file['language']=='typescript':
                        replacement='display_name' if token['token_id']==1 else 'displayName'
                    edits.append(dict(token_id=token['token_id'],replacement=replacement))
                value=dict(outcome='patch',token_edits=edits,candidate_reviews=[dict(line=p['start_line'],decision='edit',reason='rename target') for p in file['positions']],
                           rationale='rename',confidence=.5,assumptions=[])
                updated=resolve(file['source_context'],value,tokens,file['positions'])
                self.assertEqual(len(updated.splitlines()),len(file['source_context'].splitlines()))
                for before,after in zip(file['source_context'].splitlines(),updated.splitlines()):
                    self.assertEqual(len(before)-len(before.lstrip()),len(after)-len(after.lstrip()))
                if file['language']=='python':
                    import ast
                    ast.parse(updated)
                    self.assertIn('entity.display_name',updated)
                elif file['language']=='typescript':
                    self.assertIn('display_name: (entity as EntityV1).displayName',updated)
                else:
                    self.assertIn('decoded.DisplayName',updated)
                value['token_edits'][0]['replacement']='INVALID\nCODE'
                with self.assertRaises(ContractError):resolve(file['source_context'],value,tokens,file['positions'])

    def test_nonrename_is_rejected(self):
        from patchgen.rename_tokens import make_prompt
        case=json.loads((ROOT/'patchgen/fixtures/v2-identifier-bytes/runtime-input.json').read_text())
        with self.assertRaises(ContractError):make_prompt(case,case['affected_files'][0])


if __name__=='__main__':unittest.main()
