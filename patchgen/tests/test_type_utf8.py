"""Bounded migration transformations, preservation and fail-closed cases."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen.type_utf8 import transform, target, propose
from patchgen.generator import ContractError

ROOT=Path(__file__).resolve().parents[2]


class Utf8Tests(unittest.TestCase):
    def setUp(self):
        self.case=json.loads((ROOT/'patchgen/fixtures/v2-identifier-bytes/runtime-input.json').read_text())
        # Production locator also includes explicitly unchanged v1 candidates.
        for file in self.case['affected_files']:
            if file['language']=='typescript':
                file['positions'].append(dict(start_line=59,end_line=59,reason='conservative v1 candidate'))
            if file['language']=='csharp':
                file['positions'] += [dict(start_line=line,end_line=line,reason='conservative v1 candidate') for line in (15,38)]

    def test_supported_descriptor_and_roles(self):
        target(self.case)
        for file in self.case['affected_files']:
            with self.subTest(language=file['language']):
                updated,evidence=transform(file)
                self.assertEqual(len(evidence['edits']),2)
                self.assertEqual(len(updated.splitlines()),len(file['source_context'].splitlines()))
                self.assertEqual(set(evidence['candidate_decisions']),{p['start_line'] for p in file['positions']})
                if file['language']=='python':
                    self.assertIn('if version == "v2" else entity.entity_id',updated)
                    self.assertIn('if args.version == "v2" else "py_101"',updated)
                elif file['language']=='typescript':
                    self.assertIn('new TextEncoder().encode("ts_303")',updated)
                    self.assertIn('EntityV1.encode({ entityId: "ts_303", name: "Sensor C" })',updated)
                else:
                    self.assertIn('Google.Protobuf.ByteString.CopyFromUtf8("cs_202")',updated)
                    self.assertIn('["entity_id"] = decoded.EntityId.ToStringUtf8()',updated)
                    self.assertIn('new Simulation.V1.Entity { EntityId = "cs_202", Name = "Sensor B" }',updated)

    def test_unknown_candidate_rejected(self):
        for file in self.case['affected_files']:
            file['positions'].append(dict(start_line=1,end_line=1,reason='unresolved'))
            with self.subTest(language=file['language']), self.assertRaisesRegex(ContractError,'unresolved'):
                transform(file)

    def test_unsupported_bindings_rejected(self):
        mutations={'python':('module.Entity','other.Entity'),
                   'typescript':('EntityV2.decode(rawBytes)','Other.decode(rawBytes)'),
                   'csharp':('Simulation.V2.Entity','Other.Entity')}
        for file in self.case['affected_files']:
            old,new=mutations[file['language']]
            file['source_context']=file['source_context'].replace(old,new)
            with self.subTest(language=file['language']), self.assertRaises(ContractError):
                transform(file)

    def test_wrong_semantics_rejected(self):
        self.case['change']['new_schema']=self.case['change']['new_schema'].replace('bytes entity_id','int32 entity_id')
        with self.assertRaises(ContractError):target(self.case)

    def test_no_reference_or_model_use(self):
        self.case['reference_answer']='SECRET_REFERENCE'
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.generator.api',side_effect=AssertionError('no model')):
            result=propose(self.case,Path(tmp))
            self.assertNotIn('SECRET_REFERENCE',json.dumps(result))
            self.assertEqual(result['confidence'],0)
            self.assertEqual(json.loads((Path(tmp)/'assembly.json').read_text())['model_requests'],0)
