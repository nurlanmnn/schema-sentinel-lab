"""Recall-first dynamic access stays explicitly uncertain and review-blocked."""
import unittest
from patchgen.locator import scan


class DynamicCandidateTests(unittest.TestCase):
    def test_dynamic_python_reflection_forms_are_candidates(self):
        source = '''getattr (vehicle, field)
builtins.getattr(vehicle, field)
hasattr(vehicle, f"{prefix}_mps")
setattr(vehicle, choose(), value)
delattr(vehicle, field)
'''
        positions, warnings, error = scan(source, 'python', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [1,2,3,4,5])
        self.assertEqual([w['line'] for w in warnings], [1,2,3,4,5])
        self.assertFalse(error)
        self.assertTrue(all(p['resolution'] == 'candidate' and not p.get('binding_evidence') for p in positions))

    def test_escaped_python_literal_keys_use_their_value(self):
        source = 'getattr(vehicle, "speed\\x5fmps")\nfields = {"speed\\u005fmps": value}\ngetattr(vehicle, "unrelated")\n'
        positions, warnings, error = scan(source, 'python', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [1,2])
        self.assertFalse(warnings)
        self.assertFalse(error)

    def test_bounded_subscript_heuristic_keeps_fixed_literal_keys_out(self):
        snippets = {'python': 'entity[key]\nentity["unrelated"]\nentity[0]\n',
                    'typescript': 'entity[key];\nentity["unrelated"];\nentity[0];\n',
                    'csharp': 'class C { void F() {\nvar x = entity[key];\nvar y = entity["unrelated"];\nvar z = entity[0];\n}}'}
        for language, source in snippets.items():
            with self.subTest(language=language):
                positions, warnings, error = scan(source, language, 'speed_mps')
                self.assertEqual([p['start_line'] for p in positions], [2] if language == 'csharp' else [1])
                self.assertEqual(len(warnings), 1)
                self.assertFalse(error)

    def test_unrelated_reflection_is_conservative_and_explicit(self):
        positions, warnings, _ = scan('class C { void F() { other.GetProperty(key); }}', 'csharp', 'speed_mps')
        self.assertEqual(len(positions), 1)
        self.assertEqual(len(warnings), 1)
        self.assertIn('identity unknown', positions[0]['reason'])

    def test_arbitrary_subscript_receivers_remain_a_visible_scope_limit(self):
        positions, warnings, error = scan('vehicle[key]\n', 'python', 'speed_mps')
        self.assertFalse(positions)
        self.assertFalse(error)
