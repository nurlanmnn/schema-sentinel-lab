"""Launcher boundaries that matter before installing or starting runtimes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_demo


class DemoTests(unittest.TestCase):
    def test_existing_output_rejected_without_preflight(self):
        with tempfile.TemporaryDirectory() as tmp, patch('run_demo.preflight') as preflight:
            with self.assertRaisesRegex(RuntimeError, 'new directory'):
                run_demo.execute('utf8', Path(tmp))
            preflight.assert_not_called()

    def test_missing_pinned_history_is_actionable(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('run_local.check_tools'), patch('run_demo.shutil.which', return_value='/tool'), \
             patch('run_demo.subprocess.run') as run:
            run.return_value.returncode = 1
            with self.assertRaisesRegex(RuntimeError, 'full clone'):
                run_demo.preflight('rename', Path(tmp) / 'new')
            self.assertFalse((Path(tmp) / 'new').exists())

    def test_occupied_port_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('run_local.check_tools'), patch('run_demo.shutil.which', return_value='/tool'), \
             patch('run_demo.subprocess.run') as run, patch('run_demo.socket.socket') as socket:
            run.return_value.returncode = 0
            socket.return_value.__enter__.return_value.bind.side_effect = OSError('busy')
            with self.assertRaisesRegex(RuntimeError, 'Port 8000'):
                run_demo.preflight('utf8', Path(tmp) / 'new')
            self.assertFalse((Path(tmp) / 'new').exists())

    def test_install_failure_retains_report_and_log_without_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp, patch('run_demo.preflight', return_value={'source_revision': 'a'*40}), \
             patch('run_demo.subprocess.check_output', return_value='Python 3.13.7'), \
             patch('run_demo.subprocess.run', side_effect=OSError('installer unavailable')):
            output = Path(tmp) / 'new'
            self.assertEqual(run_demo.execute('utf8', output), 1)
            report = json.loads((output / 'demo-report.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertIn('installer unavailable', report['error'])
            self.assertTrue((output / 'demo.log').exists())
            self.assertFalse((output / 'run').exists())

    def test_existing_incompatible_environment_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as tmp, patch('run_demo.preflight', return_value={'source_revision': 'a'*40}), \
             patch('run_demo.subprocess.check_output', return_value='Python 3.10.0'), \
             patch('run_demo.subprocess.run') as run:
            output = Path(tmp) / 'new'
            self.assertEqual(run_demo.execute('utf8', output), 1)
            run.assert_not_called()
            self.assertIn('Existing .venv', json.loads((output/'demo-report.json').read_text())['error'])


if __name__ == '__main__':
    unittest.main()
