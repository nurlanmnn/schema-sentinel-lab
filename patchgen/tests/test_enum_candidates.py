"""Enum syntax evidence must not promote incomplete analysis to generation."""
import json
from pathlib import Path
import tempfile
import unittest
from patchgen.detector import detect
from patchgen.locator import enum_symbols, scan_enum, locate
from patchgen.adapter import adapt, coverage
from patchgen.corpus import seed, CORPUS
from patchgen.generator import ContractError


class EnumCandidateTests(unittest.TestCase):
    def record(self, old, new):
        return detect(old, new, 'model.proto', 'a'*40, 'enum-test', 'New enum state needs explicit predicate policy.')

    def test_nested_enum_fields_and_generated_names(self):
        old = '''syntax="proto3"; package demo;
        message Packet { enum LinkState { LINK_STATE_UNKNOWN=0; LINK_STATE_UP=1; }
          LinkState link_state=1;
          message Nested { LinkState previous_state=1; }
        }'''
        new = old.replace('LINK_STATE_UP=1;', 'LINK_STATE_UP=1; LINK_STATE_PAUSED=2;')
        analysis = enum_symbols(self.record(old, new))
        self.assertEqual(analysis['enum'], 'demo.Packet.LinkState')
        self.assertEqual({f['name'] for f in analysis['fields']}, {'link_state', 'previous_state'})
        self.assertTrue({'LinkState', 'LINK_STATE_UP', 'LinkStateUp', 'Up', 'link_state'} <= set(analysis['symbols']))
        self.assertEqual(analysis['status'], 'candidate_only')

    def test_constant_predicates_switch_and_numeric_field_access(self):
        symbols = ['StockState', 'state', 'STOCK_AVAILABLE', 'StockAvailable']
        snippets = {
            'python': 'if item.state == STOCK_AVAILABLE:\n    fulfill()\nif item.state == 1:\n    audit()\n',
            'typescript': 'switch (item.state) { case StockState.STOCK_AVAILABLE: fulfill(); break; }\n',
            'csharp': 'class T { bool Can(Item item) => item.State == StockState.StockAvailable; }\n'}
        for language, source in snippets.items():
            with self.subTest(language=language):
                positions, _, error = scan_enum(source, language, symbols)
                self.assertFalse(error)
                self.assertEqual({p['start_line'] for p in positions}, {1,3} if language == 'python' else {1})

    def test_active_candidates_keep_adapter_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, revision = seed('inventory', Path(tmp))
            detector = detect((source/'model.proto').read_text(),
                (CORPUS/'inventory/inventory-state-backorder.proto').read_text(),
                'model.proto', revision, 'inventory-active', 'BACKORDERED cannot fulfill orders.')
            located = locate(source, detector)
            self.assertEqual(located['status'], 'partial')
            self.assertEqual(len(located['files']), 3)
            self.assertTrue(located['enum_analysis']['fields'])
            with self.assertRaisesRegex(ContractError, 'incomplete'):
                adapt(source, detector, located)

    def test_parse_and_dynamic_warnings_retained(self):
        _, warnings, _ = scan_enum('getattr(item, field)\n', 'python', ['state'])
        self.assertTrue(warnings)
        self.assertTrue(scan_enum('const x = (', 'typescript', ['state'])[2])


if __name__ == '__main__':
    unittest.main()
