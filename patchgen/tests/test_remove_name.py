"""Removal must preserve retained fields and reject unrecognized executable uses."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen.remove_name import target, transform, propose
from patchgen.generator import ContractError

ROOT = Path(__file__).resolve().parents[2]


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((ROOT/'patchgen/fixtures/entity-name-removal/runtime-input.json').read_text())

    def test_supported_removal_preserves_retained_fields_and_v2(self):
        target(self.case)
        for file in self.case['affected_files']:
            with self.subTest(language=file['language']):
                updated, edits = transform(file)
                self.assertEqual(len(edits), 2)
                self.assertNotIn('entity.name', updated)
                self.assertNotIn('decoded.Name', updated)
                self.assertNotIn('name: "Sensor C"', updated)
                for line in file['source_context'].splitlines():
                    if 'EntityV2.encode' in line or 'new Simulation.V2.Entity' in line:
                        self.assertIn(line, updated)
                self.assertIn('entity_id', updated)

    def test_reservation_and_field_shape_required(self):
        for old, new in [('reserved 2;', ''), ('reserved "name";', '')]:
            case = copy.deepcopy(self.case)
            case['change']['new_schema'] = case['change']['new_schema'].replace(old, new)
            with self.subTest(old=old), self.assertRaisesRegex(ContractError, 'reserved'):
                target(case)
        self.case['change']['old_schema'] = self.case['change']['old_schema'].replace('string name', 'repeated string name')
        with self.assertRaises(ContractError):
            target(self.case)

    def test_side_effectful_constructors_not_silently_deleted(self):
        mutations = {'python': ('"Sensor A"', 'load_name()'),
                     'typescript': ('"Sensor C"', 'loadName()'), 'csharp': ('"Sensor B"', 'LoadName()')}
        for file in self.case['affected_files']:
            old, new = mutations[file['language']]
            file['source_context'] = file['source_context'].replace(old, new)
            with self.subTest(language=file['language']), self.assertRaises(ContractError):
                transform(file)

    def test_changed_binding_and_observation_rejected(self):
        mutations = {'python': ('fields["name"] = entity.name', 'print(entity.name)'),
                     'typescript': ('(entity as EntityV1).name', 'other.name'),
                     'csharp': ('Simulation.V1.Entity.Parser', 'Other.Entity.Parser')}
        for file in self.case['affected_files']:
            old, new = mutations[file['language']]
            file['source_context'] = file['source_context'].replace(old, new)
            with self.subTest(language=file['language']), self.assertRaises(ContractError):
                transform(file)

    def test_unknown_candidate_and_unlisted_token_rejected(self):
        for file in self.case['affected_files']:
            unknown = copy.deepcopy(file)
            unknown['positions'].append(dict(start_line=1, end_line=1))
            with self.subTest(language=file['language']), self.assertRaisesRegex(ContractError, 'Unresolved'):
                transform(unknown)
            file['positions'].pop()
            with self.assertRaisesRegex(ContractError, 'outside'):
                transform(file)

    def test_python_guard_with_other_work_is_not_deleted(self):
        file = self.case['affected_files'][0]
        file['source_context'] = file['source_context'].replace('fields["name"] = entity.name',
            'fields["name"] = entity.name\n        print("keep me")')
        with self.assertRaises(ContractError):
            transform(file)

    def test_no_model_or_reference_use(self):
        self.case['reference_answer'] = 'SECRET_REFERENCE'
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.generator.api', side_effect=AssertionError('model call')):
            proposal = propose(self.case, Path(tmp))
            self.assertNotIn('SECRET_REFERENCE', json.dumps(proposal))
            self.assertEqual(json.loads((Path(tmp)/'assembly.json').read_text())['model_requests'], 0)


if __name__ == '__main__':
    unittest.main()
