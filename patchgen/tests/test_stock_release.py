"""The stock allow-list is opt-in and tied to exact locator evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from patchgen.adapter import adapt
from patchgen.detector import detect
from patchgen.generator import ContractError
from patchgen.locator import locate
from patchgen.stock_release import prepare, propose

ROOT = Path(__file__).resolve().parents[2]


class StockReleaseTests(unittest.TestCase):
    def test_pinned_release_requires_all_consumer_candidates(self):
        fixture = json.loads((ROOT / 'patchgen/fixtures/inventory-stock-release/runtime-input.json').read_text())
        change = fixture['change']
        detector = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                          fixture['source_revision'], change['id'], fixture['intended_behavior'])
        locator = locate(ROOT, detector)
        with self.assertRaisesRegex(ContractError, 'incomplete or ambiguous'):
            adapt(ROOT, detector, locator)
        case, _ = prepare(ROOT, detector, locator)
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.assertIn('STOCK_STATE_RELEASED', propose(case, output)['diff'])
            case['affected_files'][0]['positions'].clear()
            with self.assertRaisesRegex(ContractError, 'unresolved stock release role'):
                propose(case, output)
