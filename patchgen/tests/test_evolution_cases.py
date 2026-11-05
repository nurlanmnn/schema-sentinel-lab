"""New classifications require isolated changes and exact reservations."""
import json
from pathlib import Path
import unittest

from patchgen.detector import compare, descriptor

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    'telemetry-tag-move': 'field_renumbered',
    'telemetry-json-key': 'field_json_name_changed',
    'inventory-packed-bins': 'field_packing_changed',
    'inventory-routing-oneof': 'fields_grouped_in_oneof',
    'inventory-state-retirement': 'enum_value_retired',
}


class EvolutionCaseTests(unittest.TestCase):
    def test_expected_categories_and_companion_option_rejection(self):
        for name, category in CASES.items():
            with self.subTest(case=name):
                path = ROOT / 'patchgen/fixtures' / name / 'runtime-input.json'
                change = json.loads(path.read_text())['change']
                old, _ = descriptor(change['old_schema'], change['schema_path'])
                new, _ = descriptor(change['new_schema'], change['schema_path'])
                events, unsupported = compare(old, new)
                self.assertEqual([event['category'] for event in events], [category])
                self.assertEqual(unsupported, [])
                new.options.deprecated = True
                self.assertTrue(compare(old, new)[1])

    def test_reservations_are_required_for_moves_and_retirements(self):
        for name in ('telemetry-tag-move', 'inventory-state-retirement'):
            with self.subTest(case=name):
                path = ROOT / 'patchgen/fixtures' / name / 'runtime-input.json'
                change = json.loads(path.read_text())['change']
                old, _ = descriptor(change['old_schema'], change['schema_path'])
                new, _ = descriptor(change['new_schema'], change['schema_path'])
                owner = new.message_type[0] if name == 'telemetry-tag-move' else new.enum_type[0]
                owner.ClearField('reserved_range')
                events, unsupported = compare(old, new)
                self.assertNotIn(CASES[name], [event['category'] for event in events])
                self.assertTrue(unsupported)
