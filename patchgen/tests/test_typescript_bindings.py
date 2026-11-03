"""Positive source provenance and independently authored TS scope counterexamples."""
import unittest
import copy
import json
from pathlib import Path
import subprocess
import tempfile
from patchgen.adapter import adapt
from patchgen.detector import detect
from patchgen.locator import locate, scan, attach_bindings
from patchgen.generator import ContractError, resolve_candidates, edit_prompt
from patchgen.typescript_bindings import references

IMPORT = 'import { VehicleTelemetry as V } from "../../generated/ts/telemetry/vehicle";\n'
PATH = 'runtimes/typescript/telemetry.ts'
ROOT = Path(__file__).resolve().parents[2]


def bound(source):
    return references(source, 'speed_mps', 'generated/ts/telemetry/vehicle', 'VehicleTelemetry', PATH)


class TypeScriptBindingTests(unittest.TestCase):
    def test_decode_alias_threshold_and_encode_object(self):
        source = IMPORT + '''function run(payload: Uint8Array) {
  const Codec = V;
  const e = Codec.decode(payload);
  const alias = e;
  const sample = Codec.encode({speedMps: 1}).finish();
  return alias.speedMps > 30, e["speedMps"];
}
'''
        refs, _ = bound(source)
        self.assertEqual([r['line'] for r in refs], [6,7,7])
        self.assertEqual(refs[1]['evidence'][-1]['name'], 'alias')

    def test_exact_module_and_namespace_import(self):
        source = 'import * as pb from "../../generated/ts/telemetry/vehicle";\nconst e = pb.VehicleTelemetry.decode(data);\nconsole.log(e.speedMps);\n'
        self.assertEqual([r['line'] for r in bound(source)[0]], [3])
        for changed in ('../../generated/ts/v1/vehicle', '../../generated/ts/telemetry/other'):
            with self.subTest(module=changed):
                self.assertFalse(bound(source.replace('../../generated/ts/telemetry/vehicle', changed))[0])

    def test_type_only_imports_and_casts_cannot_establish_identity(self):
        examples = [
            'import type { VehicleTelemetry as V } from "../../generated/ts/telemetry/vehicle";\nconst e = V.decode(data);\ne.speedMps;',
            'import { type VehicleTelemetry as V } from "../../generated/ts/telemetry/vehicle";\nconst e = V.decode(data);\ne.speedMps;',
            IMPORT + 'const e = other as V;\ne.speedMps;',
            IMPORT + 'const e: V = other;\ne.speedMps;',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(source)[0])

    def test_parameters_hoisting_and_nested_capture_shadow_imports(self):
        examples = [
            'function f(V: any) { const e = V.decode(data); return e.speedMps; }',
            'function f() { const e = V.decode(data); var V = other; return e.speedMps; }',
            'function f(V: any) { return () => { const e = V.decode(data); return e.speedMps; }; }',
            'function f() { const V = other; return () => { const e = V.decode(data); return e.speedMps; }; }',
            'function f() { const e = V.decode(data); return () => e.speedMps; }',
            'function f({V}: any) { const e = V.decode(data); return e.speedMps; }',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(IMPORT+source)[0])

    def test_loop_class_and_nested_scope_shadowing_remain_unknown(self):
        examples = [
            'function outer() { for (const V of others) { run(() => { const e = V.decode(data); return e.speedMps; }); } }',
            'for (const V of others) { run(() => { const e = V.decode(data); return e.speedMps; }); }',
            'function outer() { class V {} run(() => { const e = V.decode(data); return e.speedMps; }); }',
            'const X = class V { f() { const e = V.decode(data); return e.speedMps; } };',
            'namespace N { import V = Other; export function f() { const e = V.decode(data); return e.speedMps; } }',
            'import { Other as V } from "elsewhere"; const e = V.decode(data); e.speedMps;',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(IMPORT+source)[0])

    def test_arrow_body_has_its_own_immutable_decode_evidence(self):
        source = IMPORT + 'const results = requests.map(request => {\n  const e = V.decode(request.payload);\n  return e.speedMps > 30;\n});\n'
        self.assertEqual([r['line'] for r in bound(source)[0]], [4])

    def test_mutable_assignments_and_branch_joins_stay_candidates(self):
        examples = [
            'let e = V.decode(data); e = other; e.speedMps;',
            'let e; if (flag) { e = V.decode(data); } e.speedMps;',
            'let e = V.decode(data); for (e of others) {} e.speedMps;',
            'let e = V.decode(data); items.forEach(() => { e = other; }); e.speedMps;',
            'let e = V.decode(data); flag ? e = other : nothing; e.speedMps;',
            'const e = flag ? V.decode(data) : other; e.speedMps;',
        ]
        for source in examples:
            with self.subTest(source=source): self.assertFalse(bound(IMPORT+source)[0])

    def test_codec_mutation_and_const_reassignment_disable_evidence(self):
        examples = [
            'V.decode = other;',
            'const Alias = V; class C { f() { Alias.decode = other; } }',
            'Object.assign(V, {decode: other});',
            'Reflect.set(V, "decode", other);',
            'Object["assign"](V, {decode: other});',
            'const mutate = Object.assign; mutate(V, {decode: other});',
            'const O = Object; O.assign(V, {decode: other});',
            'const E = eval; E("mutate codec");',
            'const e = V.decode(data); (() => { e = other; })();',
        ]
        for source in examples:
            with self.subTest(source=source):
                refs, issues = bound(IMPORT+source+'\nconst sample = V.decode(data); sample.speedMps;')
                self.assertFalse(refs)
                self.assertTrue(issues)

    def test_container_and_conditional_codec_alias_mutations_disable_claims(self):
        self.assertEqual([r['line'] for r in bound(IMPORT + 'const e = V.decode(data);\ne.speedMps = 2;')[0]], [3])
        examples = [
            'const box = [V]; box[0].decode = other;',
            'const box = {codec: V}; const C = box.codec; C.decode = other;',
            'const C = flag ? V : other; C.decode = other;',
            'const C = flag && V; C.decode = other;',
            'holder.codec = V; holder.codec.decode = other;',
            'import * as pb from "../../generated/ts/telemetry/vehicle"; const C = pb["VehicleTelemetry"]; C.decode = other;',
        ]
        for source in examples:
            with self.subTest(source=source):
                refs, issues = bound(IMPORT + source + '\nconst e = V.decode(data); e.speedMps;')
                self.assertFalse(refs)
                self.assertTrue(issues)

    def test_escaped_field_token_ranges_preserve_original_utf8_source(self):
        source = IMPORT + 'const e = V.decode(data);\n' + r'console.log("é", e.sp\u0065edMps);'+'\n'
        refs, _ = bound(source)
        self.assertEqual(len(refs), 1)
        ref = refs[0]
        line = source.splitlines()[ref['line']-1].encode()
        self.assertEqual(line[ref['column']-1:ref['end_column']-1], rb'sp\u0065edMps')

    def test_type_change_attaches_provenance_without_forcing_edits(self):
        source = IMPORT + 'const e = V.decode(data);\nconsole.log(e.speedMps);\n'
        positions, _, _ = scan(source, 'typescript', 'speed_mps')
        event = dict(old_name='speed_mps', category='field_type_changed', message='simulation.telemetry.VehicleTelemetry')
        positions, _ = attach_bindings(source, 'typescript', event, None, positions,
                                      schema_path='proto/telemetry/vehicle.proto', source_path=PATH)
        self.assertEqual(len(positions), 1)
        self.assertTrue(positions[0]['binding_evidence'])
        self.assertIs(positions[0]['required_reference'], False)

    def test_rename_with_unchanged_generated_member_is_optional(self):
        source = IMPORT + 'const e = V.decode(data);\nconsole.log(e.speedMps);\n'
        for new_name, required in (('speedMps', False), ('ground_speed_mps', True)):
            positions, _, _ = scan(source, 'typescript', 'speed_mps')
            event = dict(old_name='speed_mps', new_name=new_name, category='field_renamed',
                         message='simulation.telemetry.VehicleTelemetry')
            positions, _ = attach_bindings(source, 'typescript', event, None, positions,
                                          schema_path='proto/telemetry/vehicle.proto', source_path=PATH)
            with self.subTest(new_name=new_name):
                self.assertTrue(positions[0]['binding_evidence'])
                self.assertIs(positions[0]['required_reference'], required)
        value = dict(outcome='no_change', edits=[], rationale='same generated TS member', confidence=.9,
                     assumptions=[], candidate_reviews=[dict(line=3, decision='unaffected', reason='same member')])
        positions, _, _ = scan(source, 'typescript', 'speed_mps')
        event['new_name'] = 'speedMps'
        positions, _ = attach_bindings(source, 'typescript', event, None, positions,
                                      schema_path='proto/telemetry/vehicle.proto', source_path=PATH)
        self.assertEqual(resolve_candidates(source, value, positions), source)

    def test_real_telemetry_threshold_and_adapter_tampering(self):
        fixture = json.loads((ROOT/'patchgen/fixtures/telemetry-speed-rename/runtime-input.json').read_text())
        change = fixture['change']
        detector = detect(change['old_schema'], change['new_schema'], change['schema_path'], fixture['source_revision'], change['id'], fixture['intended_behavior'])
        located = locate(ROOT, detector)
        file = next(f for f in located['files'] if f['path'] == PATH)
        self.assertEqual([p['start_line'] for p in file['positions'] if p.get('required_reference')], [9,10,11])
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp)/'source'
            subprocess.run(['git','worktree','add','--detach',str(checkout),fixture['source_revision']],cwd=ROOT,check=True,capture_output=True)
            try:
                adapted, _ = adapt(checkout, detector, located)
                for mutation in ('symbol','flag','drop_both','drop_position','drop_file'):
                    tampered = copy.deepcopy(located)
                    target = next(f for f in tampered['files'] if f['path'] == PATH)
                    position = target['positions'][-1]
                    if mutation == 'symbol': position['binding_evidence'][0]['symbol'] = 'OtherMessage'
                    elif mutation == 'flag': position['required_reference'] = False
                    elif mutation == 'drop_both':
                        position.pop('required_reference'); position.pop('binding_evidence')
                    elif mutation == 'drop_position': target['positions'].pop()
                    else: tampered['files'].remove(target)
                    with self.subTest(mutation=mutation), self.assertRaisesRegex(ContractError, 'binding|reference'):
                        adapt(checkout, detector, tampered)
            finally:
                subprocess.run(['git','worktree','remove','--force',str(checkout)],cwd=ROOT,check=True,capture_output=True)
        source = next(f for f in adapted['affected_files'] if f['path'] == PATH)
        payload = json.loads(edit_prompt(adapted, source, 'candidate_edits')[1]['content'])
        self.assertEqual(payload['prompt_version'], '2.5-binding1')
        value = dict(outcome='no_change', edits=[], rationale='generated bindings fix it', confidence=.5, assumptions=[],
                     candidate_reviews=[dict(line=11, decision='unaffected', reason='bindings')])
        with self.assertRaisesRegex(ContractError, 'bound required'):
            resolve_candidates(source['source_context'], value, [source['positions'][-1]])
