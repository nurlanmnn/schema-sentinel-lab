"""Explicit units policy and independent meter/second behavior contracts."""
import copy
import json
from pathlib import Path
import struct
import unittest
from patchgen.tests.test_type_precision import fixture as precision_fixture
from patchgen.telemetry_units import target, transform, POLICY, THRESHOLD, OBSERVATION
from patchgen.generator import ContractError, load_validation_profile
from testbed.telemetry.run import expected, requests, check_results

ROOT=Path(__file__).resolve().parents[2]


def fixture():
    result=json.loads((ROOT/'patchgen/fixtures/telemetry-speed-units/runtime-input.json').read_text())
    result['affected_files']=precision_fixture()['affected_files']
    return result


class UnitsTests(unittest.TestCase):
    def test_converts_construction_keys_predicates_and_exact_json_float(self):
        case=fixture();target(case)
        profile,diff=load_validation_profile(case,'telemetry-speed-units')
        self.assertEqual(profile['telemetry_case'],'units');self.assertEqual(diff,'')
        for file in case['affected_files']:
            updated,evidence=transform(case,file)
            self.assertIn('108.0',updated)
            self.assertIn('3.6',updated)
            self.assertNotIn('speed_mps',updated)
            self.assertNotIn('SpeedMps',updated)
            if file['language']=='csharp':self.assertIn('(double)entity.SpeedKph',updated)
            self.assertTrue(any(e['role']=='producer_mps_to_kph' for e in evidence['edits']))

    def test_each_explicit_semantic_decision_required(self):
        case=fixture()
        for phrase in (POLICY,THRESHOLD,OBSERVATION,'Runtime observation key becomes speed_kph'):
            wrong=copy.deepcopy(case);wrong['intended_behavior']=wrong['intended_behavior'].replace(phrase,'unspecified')
            with self.subTest(phrase=phrase),self.assertRaises(ContractError):target(wrong)
        wrong=copy.deepcopy(case);wrong['change']['new_schema']=wrong['change']['new_schema'].replace('float speed_kph','double speed_kph')
        with self.assertRaises(ContractError):target(wrong)

    def test_unknown_source_shape_rejected(self):
        case=fixture()
        for file in case['affected_files']:
            wrong=copy.deepcopy(file);wrong['source_context']=wrong['source_context'].replace('> 30.0','>= 30.0')
            with self.subTest(language=file['language']),self.assertRaises(ContractError):transform(case,wrong)

    def test_independent_expected_values_quantize_wire_and_preserve_decisions(self):
        wanted=expected('units');inputs=requests('units')
        self.assertEqual(wanted[2]['fields']['speed_kph'],108.0)
        self.assertFalse(wanted[2]['speeding']);self.assertTrue(wanted[3]['speeding'])
        self.assertEqual(wanted[1]['fields']['speed_kph'],struct.unpack('<f',struct.pack('<f',29.5*3.6))[0])
        for mode in ('threshold','json_rounding','producer'):
            wrong=copy.deepcopy(wanted)
            if mode=='threshold':wrong[1]['speeding']=True
            elif mode=='json_rounding':wrong[1]['fields']['speed_kph']=106.2
            else:wrong[1]['constructed_payload']=requests()[1]['payload']
            with self.subTest(mode=mode),self.assertRaises(ValueError):check_results(wrong,wanted)
        self.assertNotEqual(inputs[1]['payload'],requests()[1]['payload'])
