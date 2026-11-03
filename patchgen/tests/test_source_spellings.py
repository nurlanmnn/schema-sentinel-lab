"""Escaped names are syntax candidates, never receiver/type evidence."""
import unittest
from patchgen.locator import scan


class SourceSpellingTests(unittest.TestCase):
    def test_typescript_escaped_identifiers_and_literal_keys(self):
        source = r'''const a = vehicle.sp\u0065edMps;
const b = vehicle.sp\u{65}edMps;
const c = vehicle["speed\u004dps"];
const d = vehicle['speed\x4dps'];
const e = vehicle[`speedMps`];
const f = {"speed\u004dps": 1};
const unrelated = vehicle["other"];
'''
        positions, warnings, error = scan(source, 'typescript', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [1,2,3,4,5,6])
        self.assertFalse(warnings)
        self.assertFalse(error)
        self.assertTrue(all(p['resolution'] == 'candidate' and not p.get('binding_evidence') for p in positions))

    def test_csharp_escaped_identifiers_and_string_keys(self):
        source = r'''class C { void F() {
var a = vehicle.Sp\u0065edMps;
var b = vehicle.@SpeedMps;
var c = vehicle["Speed\u004dps"];
var d = vehicle[@"SpeedMps"];
var e = vehicle["Speed\x004dps"];
var f = vehicle["Speed\U0000004dps"];
var unrelated = vehicle[@"other"];
}}
'''
        positions, warnings, error = scan(source, 'csharp', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [2,3,4,5,6,7])
        self.assertFalse(warnings)
        self.assertFalse(error)

    def test_csharp_formatting_characters_and_escaped_reflection_member(self):
        source = 'class C { void F() {\nvar a = vehicle.Speed\u200cMps;\n' + r'var b = type.GetPro\u0070erty(key);' + '\n}}'
        positions, warnings, error = scan(source, 'csharp', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [2,3])
        self.assertEqual([w['line'] for w in warnings], [3])
        self.assertFalse(error)

    def test_python_normalized_reflection_and_dynamic_receiver_spellings(self):
        source = 'ｇｅｔａｔｔｒ(vehicle, key)\nｅｎｔｉｔｙ[key]\n'
        positions, warnings, error = scan(source, 'python', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [1,2])
        self.assertEqual([w['line'] for w in warnings], [1,2])
        self.assertFalse(error)

    def test_string_values_do_not_get_identifier_normalization(self):
        source = 'vehicle["ｓｐｅｅｄ_ｍｐｓ"]\ngetattr(vehicle, "ｓｐｅｅｄ_ｍｐｓ")\n'
        self.assertFalse(scan(source, 'python', 'speed_mps')[0])

    def test_javascript_identifier_normalization_is_not_python_normalization(self):
        source = 'const a = vehicle.ｓｐｅｅｄMps;\nconst b = vehicle["ｓｐｅｅｄMps"];\n'
        self.assertFalse(scan(source, 'typescript', 'speed_mps')[0])

    def test_csharp_verbatim_backslashes_are_not_decoded(self):
        source = r'class C { void F() { var a = vehicle[@"Speed\u004dps"]; }}'
        self.assertFalse(scan(source, 'csharp', 'speed_mps')[0])

    def test_interpolated_typescript_template_stays_uncertain(self):
        source = 'const a = entity[`speed${suffix}`];\n'
        positions, warnings, error = scan(source, 'typescript', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [1])
        self.assertTrue(warnings)
        self.assertFalse(error)

    def test_named_field_literal_and_index_use_are_both_candidates(self):
        examples = [
            ('python', 'key = "speed_mps"\nprint(vehicle[key])\n', [1, 2]),
            ('typescript', 'const key = `speedMps`;\nvehicle[key];\n', [1, 2]),
            ('csharp', 'class C { void F() {\nconst string key = @"SpeedMps";\nvar a = vehicle[key];\n}}\n', [2, 3]),
        ]
        for language, source, expected in examples:
            with self.subTest(language=language):
                positions, warnings, error = scan(source, language, 'speed_mps')
                self.assertEqual([p['start_line'] for p in positions], expected)
                self.assertFalse(warnings)
                self.assertFalse(error)
                self.assertTrue(all(p['resolution'] == 'candidate' and not p.get('binding_evidence') for p in positions))

    def test_named_key_heuristic_does_not_flag_unrelated_or_unknown_indexing(self):
        examples = [
            ('python', 'unused = "speed_mps"\nkey = "Authorization"\nprint(headers[key], vehicle[external])\n'),
            ('typescript', 'const unused = "speedMps";\nconst key = "Authorization";\nheaders[key]; vehicle[external];\n'),
            ('csharp', 'class C { void F() {\nvar unused = "SpeedMps";\nvar key = "Authorization";\nvar a = headers[key]; var b = vehicle[external];\n}}\n'),
        ]
        for language, source in examples:
            with self.subTest(language=language):
                self.assertEqual(scan(source, language, 'speed_mps'), ([], [], False))
