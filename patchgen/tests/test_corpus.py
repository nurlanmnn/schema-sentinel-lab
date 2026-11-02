"""Domain benchmark evidence must distinguish support, rejection and migration."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen import corpus


class CorpusTests(unittest.TestCase):
    def test_authored_scenarios_have_expected_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.generator.api', side_effect=AssertionError('model call')):
            summary = corpus.run(Path(tmp) / 'run')
            self.assertEqual(summary['scenario_count'], 8)
            self.assertEqual(summary['expectation_matches'], 8)
            self.assertEqual(summary['detector_complete'], 5)
            self.assertEqual(summary['locator_complete'], 4)
            self.assertEqual(summary['generated_validated_migrations'], 0)
            self.assertFalse(any('error' in r for r in summary['records']))
            measured = [r['measurement'] for r in summary['records'] if r['measurement']]
            self.assertEqual(sum(m['expected_sites'] for m in measured), 45)
            self.assertEqual(sum(m['matched_sites'] for m in measured), 45)
            self.assertFalse(any(m['missed'] for m in measured))
            self.assertEqual(sum(len(m['extra']) for m in measured), 2)
            rejected = next(r for r in summary['records'] if r['id'] == 'inventory-state-backorder')
            self.assertEqual(rejected['locator_status'], 'partial')
            self.assertFalse((Path(tmp)/'run/inventory-state-backorder/input.json').exists())

    def test_scoring_failure_cannot_keep_matching_status(self):
        with tempfile.TemporaryDirectory() as tmp, patch('patchgen.corpus.coverage', side_effect=KeyError('broken scorer')):
            summary = corpus.run(Path(tmp) / 'run')
            failed = [r for r in summary['records'] if 'error' in r]
            self.assertEqual(len(failed), 5)
            self.assertTrue(all(not r['expectation_match'] for r in failed))
            self.assertEqual(summary['expectation_matches'], 3)

    def test_seed_revision_is_reconstructible(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, ra = corpus.seed('telemetry', Path(tmp)/'first')
            b, rb = corpus.seed('telemetry', Path(tmp)/'second')
            self.assertEqual(ra, rb)
            self.assertEqual((a/'model.proto').read_bytes(), (b/'model.proto').read_bytes())


if __name__ == '__main__':
    unittest.main()
