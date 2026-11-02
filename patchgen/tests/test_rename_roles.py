import copy
import json
import unittest
from pathlib import Path
from patchgen.rename_roles import make_prompt, resolve
from patchgen.generator import ContractError

ROOT = Path(__file__).resolve().parents[2]


class RoleRenameTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT/'patchgen/fixtures/entity-name-rename/runtime-input.json').read_text())

    def proposal(self, file, tokens):
        return dict(outcome='patch', token_edits=[dict(token_id=t['token_id'], replacement=t['allowed'][0]) for t in tokens],
                    candidate_reviews=[dict(line=p['start_line'], decision='edit', reason='rename target') for p in file['positions']],
                    rationale='rename', confidence=.5, assumptions=[])

    def test_names_follow_syntax_roles(self):
        file = self.case['affected_files'][1]
        messages, tokens = make_prompt(self.case, file)
        self.assertEqual(json.loads(messages[1]['content'])['prompt_version'], '2.7')
        self.assertEqual([(t['role'], t['allowed']) for t in tokens], [
            ('canonical_observation_key',['display_name']),
            ('generated_property',['displayName']),
            ('generated_construction_key',['displayName'])])
        value = self.proposal(file,tokens)
        result = resolve(file['source_context'], value, tokens, file['positions'])
        self.assertIn('display_name: (entity as EntityV1).displayName',result)
        self.assertIn('entityId: "ts_303", displayName:',result)
        value['token_edits'][2]['replacement'] = 'display_name'
        with self.assertRaises(ContractError): resolve(file['source_context'], value, tokens, file['positions'])

    def test_missing_python_observation_key_rejected(self):
        file = self.case['affected_files'][0]
        _,tokens = make_prompt(self.case,file)
        value = self.proposal(file,tokens)
        value['token_edits'].pop(0)
        with self.assertRaisesRegex(ContractError,'all rename tokens'):
            resolve(file['source_context'],value,tokens,file['positions'])

    def test_unrecognized_ts_object_role_rejected(self):
        file = copy.deepcopy(self.case['affected_files'][1])
        file['source_context'] = 'const unrelated = { name: "value" };\n'
        file['positions'] = [dict(start_line=1,end_line=1,reason='candidate')]
        with self.assertRaisesRegex(ContractError,'unsupported TypeScript'):
            make_prompt(self.case,file)

    def test_unaffected_line_keeps_every_token(self):
        file = self.case['affected_files'][0]
        _,tokens = make_prompt(self.case,file)
        value = self.proposal(file,tokens)
        line = tokens[0]['line']
        value['token_edits'] = [e for e in value['token_edits'] if e['token_id'] not in {t['token_id'] for t in tokens if t['line']==line}]
        value['candidate_reviews'][0]['decision']='unaffected'
        updated=resolve(file['source_context'],value,tokens,file['positions'])
        self.assertEqual(updated.splitlines()[line-1], file['source_context'].splitlines()[line-1])

    def test_requires_explicit_observation_policy(self):
        self.case['intended_behavior']='Rename field only.'
        with self.assertRaisesRegex(ContractError,'unsupported TypeScript'):
            make_prompt(self.case,self.case['affected_files'][1])

    def test_generator_request_and_assembly_without_service(self):
        import tempfile
        from unittest.mock import patch
        from patchgen.generator import generate
        def api(endpoint, route, data=None):
            if route == '/api/tags': return {'models':[{'name':'ministral-3:8b'}]}
            if route == '/api/ps': return {'models':[]}
            if route == '/api/chat':
                payload=json.loads(data['messages'][1]['content'])
                self.assertEqual(payload['prompt_version'],'2.7')
                tokens=payload['syntax_tokens']
                file=payload['affected_files'][0]
                value=self.proposal(file,tokens)
                return {'done':True,'message':{'content':json.dumps(value)}}
            return {}
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.generator.api',side_effect=api):
            proposal=generate(self.case,'ministral-3:8b','http://127.0.0.1:11434',Path(tmp),'syntax_rename_roles')
            self.assertEqual(proposal['outcome'],'patch')
            self.assertIn('+        fields["display_name"] = entity.display_name',proposal['diff'])
            self.assertIn('displayName: "Sensor C"',proposal['diff'])

    def test_deterministic_proposal_uses_no_model_or_reference_fields(self):
        import tempfile
        from unittest.mock import patch
        from patchgen.rename_roles import propose
        self.case['reference_answer']='SECRET_REFERENCE'
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.generator.api',side_effect=AssertionError('no model calls')):
            result=propose(self.case,Path(tmp))
            self.assertNotIn('SECRET_REFERENCE',json.dumps(result))
            assembly=json.loads((Path(tmp)/'assembly.json').read_text())
            self.assertEqual(assembly['model_requests'],0)
            self.assertEqual(result['confidence'],0)
            self.assertIn('fields["display_name"] = entity.display_name',result['diff'])
            self.assertNotIn('-    if version == "v1":',result['diff'])
