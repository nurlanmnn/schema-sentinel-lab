"""Independent positive and adversarial source examples for bounded binding claims."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from patchgen.python_bindings import references
from patchgen.locator import scan, attach_bindings, locate
from patchgen.detector import detect
from patchgen.generator import ContractError, resolve_candidates, edit_prompt
from patchgen.adapter import adapt

ROOT = Path(__file__).resolve().parents[2]
IMPORT = 'from fleet.vehicle_pb2 import Vehicle as V\n'


def bound(source):
    return references(source, 'speed_mps', 'fleet.vehicle_pb2', 'Vehicle')


class BindingTests(unittest.TestCase):
    def test_constructor_parser_alias_and_threshold(self):
        source = IMPORT + '''def evaluate(payload):
    entity = V.FromString(payload)
    sample = V(speed_mps=12.5)
    alias = entity
    return alias.speed_mps > 30.0, sample.speed_mps
'''
        refs, _ = bound(source)
        self.assertEqual([r['line'] for r in refs], [4,6,6])
        self.assertEqual(refs[1]['evidence'][-1]['name'], 'alias')

    def test_wrong_version_and_unknown_parameter_remain_candidates(self):
        source = 'from fleet.v1.vehicle_pb2 import Vehicle as V\ndef test(entity):\n    other = V(speed_mps=1)\n    return entity.speed_mps, other.speed_mps\n'
        self.assertFalse(bound(source)[0])
        positions, _, _ = scan(source, 'python', 'speed_mps')
        self.assertEqual([p['start_line'] for p in positions], [3,4])
        self.assertTrue(all(p['resolution'] == 'candidate' for p in positions))

    def test_shadowing_rebinding_and_compound_flow_cannot_keep_type(self):
        examples = [
            'def f(V):\n    e = V(speed_mps=1)\n    return e.speed_mps\n',
            'def f():\n    e = V()\n    V = other\n    return e.speed_mps\n',
            'def f():\n    e = V()\n    e = other\n    return e.speed_mps\n',
            'def f(flag):\n    e = V()\n    if flag:\n        e = other\n    return e.speed_mps\n',
            'def f():\n    e = V()\n    sink(e := other)\n    return e.speed_mps\n',
            'def f():\n    e = V()\n    return [e.speed_mps for e in unrelated]\n',
            'def f():\n    e = V()\n    def nested(e):\n        return e.speed_mps\n    return nested(other)\n',
        ]
        for example in examples:
            with self.subTest(source=example): self.assertFalse(bound(IMPORT + example)[0])

    def test_direct_module_import_and_class_alias(self):
        source = 'import fleet.vehicle_pb2 as pb\nAlias = pb.Vehicle\ne = Alias()\nprint(e.speed_mps)\n'
        self.assertEqual([r['line'] for r in bound(source)[0]], [4])

    def test_global_rebind_and_namespace_mutation_disable_claims(self):
        examples = [
            IMPORT + 'def f():\n    e = V()\n    return e.speed_mps\nV = other\n',
            IMPORT + 'Alias = V\nAlias.FromString = other\ne = V.FromString(b"a")\nprint(e.speed_mps)\n',
            IMPORT + 'e = V()\nsetattr(V, "FromString", other)\nprint(e.speed_mps)\n',
            IMPORT + 'from other import *\ne = V()\nprint(e.speed_mps)\n',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(source)[0])

    def test_match_captures_shadow_imports_and_rebind_instances(self):
        examples = [
            'def f(value):\n    e = V()\n    match value:\n        case V:\n            pass\n    return e.speed_mps\n',
            'e = V()\nmatch value:\n    case e:\n        pass\nprint(e.speed_mps)\n',
            'e = V()\nmatch value:\n    case [*e]:\n        pass\nprint(e.speed_mps)\n',
            'e = V()\nmatch value:\n    case {"key": _, **e}:\n        pass\nprint(e.speed_mps)\n',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(IMPORT + source)[0])

    def test_definition_header_rebinding_cannot_keep_import_identity(self):
        examples = [
            'def mutate(x=(V := other)):\n    pass\ne = V()\nprint(e.speed_mps)\n',
            'class C((V := other)):\n    pass\ne = V()\nprint(e.speed_mps)\n',
            '@(V := other)\ndef mutate():\n    pass\ne = V()\nprint(e.speed_mps)\n',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(IMPORT + source)[0])

    def test_hidden_and_qualified_namespace_mutations_disable_claims(self):
        examples = [
            'import builtins\nbuiltins.setattr(V, "FromString", other)\n',
            'import builtins as b\nb.setattr(V, "FromString", other)\n',
            'from builtins import setattr as mutate\nmutate(V, "FromString", other)\n',
            'vars(V)["FromString"] = other\n',
            'V.__dict__.update(FromString=other)\n',
            'class Mutator:\n    V.FromString = other\n',
            'class Mutator:\n    Alias = V\n    Alias.FromString = other\n',
        ]
        for source in examples:
            with self.subTest(source=source):
                refs, issues = bound(IMPORT + source + 'e = V.FromString(payload)\nprint(e.speed_mps)\n')
                self.assertFalse(refs)
                self.assertTrue(issues)

    def test_normalized_identifiers_keep_exact_source_byte_ranges(self):
        spelling = 'ｓｐｅｅｄ_ｍｐｓ'
        source = IMPORT + f'e = V({spelling}=1)\nprint("é", e.{spelling})\n'
        positions, _, error = scan(source, 'python', 'speed_mps')
        self.assertFalse(error)
        self.assertEqual([p['start_line'] for p in positions], [2,3])
        refs, _ = bound(source)
        self.assertEqual([r['line'] for r in refs], [2,3])
        for ref in refs:
            line = source.splitlines()[ref['line']-1].encode()
            self.assertEqual(line[ref['column']-1:ref['end_column']-1].decode(), spelling)
        event = dict(old_name='speed_mps', category='field_renamed')
        positions, _ = attach_bindings(source, 'python', event, ('fleet.vehicle_pb2','Vehicle'), positions)
        self.assertTrue(all(p.get('required_reference') for p in positions))

    def test_multiline_attribute_and_keyword_positions_point_to_field_tokens(self):
        source = IMPORT + 'e = V(\n    speed_mps=1,\n)\nprint((e\n    .speed_mps))\n'
        refs, _ = bound(source)
        self.assertEqual([r['line'] for r in refs], [3,6])
        for ref in refs:
            raw = source.splitlines()[ref['line']-1].encode()
            self.assertEqual(raw[ref['column']-1:ref['end_column']-1], b'speed_mps')

    def test_bound_required_reference_cannot_be_dismissed(self):
        positions = [dict(start_line=1, end_line=1, required_reference=True)]
        value = dict(outcome='no_change', edits=[], rationale='bindings rewrite references', confidence=.5,
                     assumptions=[], candidate_reviews=[dict(line=1, decision='unaffected', reason='generated')])
        with self.assertRaisesRegex(ContractError, 'bound required'): resolve_candidates('e.speed_mps\n', value, positions)
        value.update(outcome='needs_clarification')
        self.assertEqual(resolve_candidates('e.speed_mps\n', value, positions), 'e.speed_mps\n')

    def test_real_telemetry_threshold_has_required_binding_evidence(self):
        case = json.loads((ROOT/'patchgen/fixtures/telemetry-speed-rename/runtime-input.json').read_text())
        change = case['change']
        detector = detect(change['old_schema'], change['new_schema'], change['schema_path'], case['source_revision'], change['id'], case['intended_behavior'])
        locator = locate(ROOT, detector)
        file = next(f for f in locator['files'] if f['path'] == 'runtimes/python/telemetry_runtime.py')
        self.assertEqual([p['start_line'] for p in file['positions'] if p.get('required_reference')], [10,11,12])
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp)/'source'
            subprocess.run(['git', 'worktree', 'add', '--detach', str(checkout), case['source_revision']], cwd=ROOT, check=True, capture_output=True)
            try:
                adapted, _ = adapt(checkout, detector, locator)
                for mutation in ('symbol', 'line', 'flag', 'drop_flag', 'drop_both', 'drop_position', 'drop_file', 'drop_scan', 'stale_scan'):
                    tampered = copy.deepcopy(locator)
                    pos = next(f for f in tampered['files'] if f['language'] == 'python')['positions'][0]
                    if mutation == 'symbol': pos['binding_evidence'][0]['symbol'] = 'DifferentMessage'
                    elif mutation == 'line': pos['binding_evidence'][0]['line'] = 999
                    elif mutation == 'flag': pos['required_reference'] = False
                    elif mutation == 'drop_flag': pos.pop('required_reference')
                    elif mutation == 'drop_both':
                        pos.pop('required_reference'); pos.pop('binding_evidence')
                    elif mutation == 'drop_position':
                        next(f for f in tampered['files'] if f['language'] == 'python')['positions'].pop()
                    elif mutation == 'drop_file':
                        tampered['files'] = [f for f in tampered['files'] if f['language'] != 'python']
                    elif mutation == 'drop_scan': tampered['scanned'].pop()
                    else: tampered['scanned'][0]['source_sha256'] = '0'*64
                    with self.subTest(mutation=mutation), self.assertRaisesRegex(ContractError, 'binding|reference|manifest'):
                        adapt(checkout, detector, tampered)
            finally:
                subprocess.run(['git', 'worktree', 'remove', '--force', str(checkout)], cwd=ROOT, check=True, capture_output=True)
        source = next(f for f in adapted['affected_files'] if f['language'] == 'python')
        payload = json.loads(edit_prompt(adapted, source, 'candidate_edits')[1]['content'])
        self.assertEqual(payload['prompt_version'], '2.5-binding1')
        self.assertTrue(payload['affected_files'][0]['positions'][-1]['required_reference'])
