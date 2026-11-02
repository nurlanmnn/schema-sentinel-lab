"""Telemetry-specific proposal boundaries; live bindings are checked by retained runs."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from patchgen.generator import load_validation_profile, ContractError
from patchgen.rename_roles import inventory

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    case = json.loads((ROOT/'patchgen/fixtures/telemetry-speed-rename/runtime-input.json').read_text())
    source = subprocess.check_output(['git','show',case['source_revision']+':runtimes/typescript/telemetry.ts'],cwd=ROOT,text=True)
    case['affected_files'] = [dict(path='runtimes/typescript/telemetry.ts',language='typescript',source_context=source,
                                  positions=[dict(start_line=n,end_line=n,reason='authored test candidate') for n in (9,10,11)])]
    return case


class TelemetryPipelineTests(unittest.TestCase):
    def test_profile_pins_schema_and_source_without_test_edits(self):
        case = fixture()
        profile, diff = load_validation_profile(case,'telemetry-speed-rename')
        self.assertEqual(profile['telemetry_case'],'rename')
        self.assertEqual(diff,'')
        for field in ('source', 'schema'):
            wrong = copy.deepcopy(case)
            if field == 'source': wrong['source_revision'] = 'a'*40
            else: wrong['change']['new_schema'] += '\n'
            with self.subTest(field=field), self.assertRaises(ContractError):
                load_validation_profile(wrong,'telemetry-speed-rename')

    def test_snake_observation_key_and_camel_generated_property(self):
        case = fixture()
        tokens = inventory(case,case['affected_files'][0])
        self.assertEqual([(t['role'],t['allowed']) for t in tokens], [
            ('generated_construction_key',['groundSpeedMps']),
            ('canonical_observation_key',['ground_speed_mps']),
            ('generated_property',['groundSpeedMps']),
            ('generated_property',['groundSpeedMps'])])
        file = copy.deepcopy(case['affected_files'][0])
        file['source_context'] = file['source_context'].replace('speed_mps: entity.speedMps','speed_mps: entity.vehicleId')
        with self.assertRaisesRegex(ContractError,'unsupported TypeScript'):
            inventory(case,file)
        case['intended_behavior'] = 'Rename only; observation policy unspecified.'
        with self.assertRaises(ContractError): inventory(case,case['affected_files'][0])

    def test_profile_cannot_select_baseline_or_another_oracle(self):
        original = Path.read_text
        for modification in ({'telemetry_case':'baseline'},{'oracle_case':'entity-name-rename'}):
            def modified(path, *args, **kwargs):
                result = original(path,*args,**kwargs)
                if path.name == 'validation-profile.json' and path.parent.name == 'telemetry-speed-rename':
                    profile = json.loads(result);profile.update(modification);return json.dumps(profile)
                return result
            with self.subTest(modification=modification), patch.object(Path,'read_text',modified), self.assertRaises(ContractError):
                load_validation_profile(fixture(),'telemetry-speed-rename')
