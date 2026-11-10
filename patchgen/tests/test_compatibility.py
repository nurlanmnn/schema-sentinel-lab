"""Compatibility labels (sponsor taxonomy) and comment-change flags on detector records."""
import copy
import json
import unittest
from pathlib import Path

from patchgen.adapter import verify_detector_record
from patchgen.detector import COMPATIBILITY, SEVERITY, compatibility, descriptor, detect, element_name
from patchgen.generator import ContractError

ROOT = Path(__file__).resolve().parents[2]
OLD = '''syntax = "proto3";
message Packet {
  // Speed in meters per second.
  float speed = 1;
  string label = 2;
}
'''


def record(new, old=OLD):
    return detect(old, new, 'model.proto', 'a' * 40, 'case', 'Explain the change.')


class CompatibilityTests(unittest.TestCase):
    def test_every_category_has_a_sponsor_label_and_reason(self):
        for category, (label, reason) in COMPATIBILITY.items():
            self.assertIn(label, SEVERITY, category)
            self.assertTrue(reason, category)

    def test_overall_label_is_the_most_severe(self):
        events = [dict(category='field_renamed'), dict(category='field_removed')]
        self.assertEqual(compatibility(events, [], [])[0], 'breaking')
        self.assertEqual(compatibility([dict(category='enum_value_added')], [], [])[0], 'safe-additive')
        self.assertEqual(compatibility(events, ['something unsupported'], [])[0], 'unknown')
        self.assertEqual(compatibility([], [], [dict(element='x')])[0], 'semantic-only')
        self.assertEqual(compatibility([], [], [])[0], 'none')

    def test_records_carry_labels_per_event(self):
        renamed = record(OLD.replace('label = 2', 'caption = 2'))
        self.assertEqual(renamed['compatibility'], 'renaming')
        self.assertEqual(renamed['event_compatibility'][0]['category'], 'field_renamed')
        removed = record(OLD.replace('  string label = 2;\n', '  reserved 2;\n  reserved "label";\n'))
        self.assertEqual(removed['compatibility'], 'breaking')
        self.assertFalse(removed['semantic_review'])

    def test_comment_only_change_is_semantic_only_and_still_partial(self):
        result = record(OLD.replace('meters per second', 'kilometers per hour'))
        self.assertEqual(result['compatibility'], 'semantic-only')
        self.assertEqual(result['structural_status'], 'no_structural_change')
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(result['semantic_review'])
        self.assertEqual(result['comment_changes'], [dict(element='Packet.speed',
                         old_comment='Speed in meters per second.', new_comment='Speed in kilometers per hour.')])

    def test_whitespace_only_comment_edit_is_ignored(self):
        result = record(OLD.replace('// Speed in meters', '//   Speed   in meters'))
        self.assertEqual(result['comment_changes'], [])
        self.assertEqual(result['compatibility'], 'none')

    def test_units_fixture_is_a_rename_that_needs_semantic_review(self):
        case = json.loads((ROOT / 'patchgen/fixtures/telemetry-speed-units/runtime-input.json').read_text())
        change = case['change']
        result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                        case['source_revision'], change['id'], case['intended_behavior'])
        self.assertEqual(result['compatibility'], 'renaming')
        self.assertTrue(result['semantic_review'])
        self.assertIn('kilometers per hour', result['comment_changes'][0]['new_comment'])

    def test_element_names(self):
        file = descriptor('syntax = "proto3"; message M { string a = 1; enum E { E_X = 0; } reserved 5; }'
                          ' enum T { T_A = 0; }', 'model.proto')[0]
        self.assertEqual(element_name(file, (4, 0)), 'M')
        self.assertEqual(element_name(file, (4, 0, 2, 0)), 'M.a')
        self.assertEqual(element_name(file, (4, 0, 4, 0, 2, 0)), 'M.E.E_X')
        self.assertEqual(element_name(file, (5, 0, 2, 0)), 'T.T_A')
        self.assertEqual(element_name(file, (4, 0, 9)), 'M.reserved')
        self.assertEqual(element_name(file, (4, 7)), 'model.proto')

    def test_adapter_rejects_a_tampered_label(self):
        result = record(OLD.replace('label = 2', 'caption = 2'))
        verify_detector_record(result)
        forged = copy.deepcopy(result)
        forged['compatibility'] = 'safe-additive'
        with self.assertRaises(ContractError):
            verify_detector_record(forged)


if __name__ == '__main__':
    unittest.main()
