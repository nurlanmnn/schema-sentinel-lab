import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen.analysis_corpus import run, CATALOG


class AnalysisCorpusTests(unittest.TestCase):
    def test_component_inventories_keep_misses_extras_and_binding_claims_separate(self):
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.generator.api', side_effect=AssertionError('model call')):
            summary = run(Path(tmp)/'run')
            self.assertGreaterEqual(summary['scenario_count'], 20)
            self.assertEqual(summary['expectation_matches'], summary['scenario_count'])
            self.assertEqual((summary['candidate_expected'], summary['candidate_matched'], summary['candidate_extras']), (43,42,8))
            self.assertEqual((summary['bound_expected'], summary['bound_matched'], summary['bound_extras']), (10,10,0))
            dynamic = next(r for r in summary['records'] if r['id'] == 'dynamic-reflection')
            self.assertEqual(dynamic['candidate_coverage']['missed'], [])
            self.assertTrue(dynamic['warnings'])
            self.assertEqual(summary['validated_migrations'], 0)
            self.assertEqual(summary['model_requests'], 0)

    def test_authored_catalog_expectations_are_not_locator_inputs(self):
        original = json.loads(CATALOG.read_text())
        original['cases'][0]['expected_bound'] = []
        original_read_bytes = Path.read_bytes
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'read_bytes', autospec=True, side_effect=lambda path: json.dumps(original).encode() if path == CATALOG else original_read_bytes(path)):
            summary = run(Path(tmp)/'run')
            self.assertFalse(summary['records'][0]['expectation_match'])
            self.assertEqual(summary['records'][0]['binding_coverage']['extra'], [4])
