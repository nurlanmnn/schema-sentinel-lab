"""Bounded precision policy must reject unknown bindings, semantics and syntax."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from patchgen.generator import ContractError
from patchgen.type_precision import target, transform
from testbed.telemetry.run import expected, requests, check_results

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    case=json.loads((ROOT/'patchgen/fixtures/telemetry-speed-precision/runtime-input.json').read_text())
    files=[]
    for path,language,lines in [('runtimes/python/telemetry_runtime.py','python',[10,11,12]),
                               ('runtimes/typescript/telemetry.ts','typescript',[9,10,11]),
                               ('runtimes/csharp/Telemetry.cs','csharp',[12,13,14])]:
        files.append(dict(path=path,language=language,source_context=subprocess.check_output(
            ['git','show',case['source_revision']+':'+path],cwd=ROOT,text=True),
            positions=[dict(start_line=n,end_line=n,reason='authored test') for n in lines]))
    case['affected_files']=files
    return case


class PrecisionTests(unittest.TestCase):
    def test_supported_direct_bindings_and_only_narrowing_cast_changed(self):
        case=fixture();target(case)
        for file in case['affected_files']:
            updated,evidence=transform(file)
            if file['language']=='csharp':
                self.assertEqual(updated,file['source_context'].replace('(float)request.Speed','request.Speed'))
                self.assertEqual(len(evidence['edits']),1)
            else:
                self.assertEqual(updated,file['source_context'])
                self.assertEqual(evidence['edits'],[])

    def test_wrong_units_cardinality_and_other_types_rejected(self):
        case=fixture()
        for kind in ('policy','optional','repeated','other_type'):
            wrong=copy.deepcopy(case)
            if kind=='policy':wrong['intended_behavior']='Convert to km/h.'
            elif kind=='optional':wrong['change']['new_schema']=wrong['change']['new_schema'].replace('double speed_mps','optional double speed_mps')
            elif kind=='repeated':wrong['change']['new_schema']=wrong['change']['new_schema'].replace('double speed_mps','repeated double speed_mps')
            else:wrong['change']['new_schema']=wrong['change']['new_schema'].replace('double speed_mps','int64 speed_mps')
            with self.subTest(kind=kind), self.assertRaises(ContractError):target(wrong)

    def test_unknown_threshold_binding_or_input_precision_rejected(self):
        case=fixture()
        for file in case['affected_files']:
            wrong=copy.deepcopy(file);wrong['source_context']=wrong['source_context'].replace('> 30.0','>= 30.0')
            with self.subTest(language=file['language']),self.assertRaises(ContractError):transform(wrong)
        wrong=copy.deepcopy(case['affected_files'][2]);wrong['source_context']=wrong['source_context'].replace('double Speed','float Speed')
        with self.assertRaises(ContractError):transform(wrong)
        wrong=copy.deepcopy(case['affected_files'][0]);wrong['source_context']=wrong['source_context'].replace('from telemetry.vehicle_pb2','from wrong.vehicle_pb2')
        with self.assertRaises(ContractError):transform(wrong)
        wrong=copy.deepcopy(case['affected_files'][1]);wrong['positions'].pop()
        with self.assertRaises(ContractError):transform(wrong)

    def test_precision_cases_distinguish_rounding_and_threshold(self):
        import struct
        cases=requests('precision');wanted=expected('precision')
        self.assertEqual(len(cases),11)
        self.assertEqual(set(wanted[0]['fields']),{'vehicle_id','speed_mps'})
        self.assertTrue(wanted[8]['speeding']);self.assertFalse(wanted[9]['speeding'])
        self.assertEqual(struct.unpack('<f',struct.pack('<f',cases[8]['speed']))[0],30.0)
        actual=copy.deepcopy(wanted);actual[8]['constructed_payload']=actual[2]['constructed_payload']
        with self.assertRaises(ValueError):check_results(actual,wanted)
