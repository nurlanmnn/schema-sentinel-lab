import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ExplainChangeTests(unittest.TestCase):
    def test_default_fixture_prints_both_stages(self):
        result = subprocess.run([sys.executable, 'explain_change.py'], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        self.assertIn("'category': 'field_renamed'", result.stdout)
        self.assertIn('STEP 2 - IMPACT LOCATION', result.stdout)
        self.assertIn('runtimes/typescript/telemetry.ts', result.stdout)
        self.assertIn('[bound, must edit]', result.stdout)


if __name__ == '__main__':
    unittest.main()
