"""Suite denominators and failure evidence are evaluation requirements."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_benchmark as suite


class SuiteTests(unittest.TestCase):
    def test_manifest_counts_distinct_migrations_only(self):
        entries = suite.manifest()
        self.assertEqual(len(entries), 20)
        self.assertEqual(len({e['profile'] for e in entries}), 20)
        self.assertEqual(sum(e['expected_sites'] for e in entries), 137)

    def test_missing_report_keeps_failed_case_in_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = suite.manifest()[0]
            missing = suite.collect(entry, Path(tmp) / entry['case'], 1, 0.1)
            self.assertFalse(missing['measurement_available'])
            metrics = suite.summarize([missing])
            self.assertEqual(metrics['expected_sites'], 6)
            self.assertEqual(metrics['validation_rate'], 0)
            self.assertEqual(metrics['impact_recall'], 0)
            self.assertEqual(metrics['classification_accuracy'], 0)

    def test_pass_label_alone_cannot_count_as_validated_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'case'
            (target / 'run').mkdir(parents=True)
            (target / 'demo-report.json').write_text(json.dumps({'status': 'validation_passed'}))
            report = {'status': 'validation_passed', 'measurement': {
                'expected_sites': 6, 'matched_sites': 6, 'extra': [], 'classification_correct': True}}
            (target / 'run/report.json').write_text(json.dumps(report))
            row = suite.collect(suite.manifest()[0], target, 0, 0.1)
            self.assertEqual(row['status'], 'failed')
            self.assertEqual(suite.summarize([row])['impact_recall'], 1)

    def test_incompatible_ground_truth_count_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'case'
            (target / 'run').mkdir(parents=True)
            (target / 'demo-report.json').write_text('{}')
            (target / 'run/report.json').write_text(json.dumps({'measurement': {'expected_sites': 999}}))
            row = suite.collect(suite.manifest()[0], target, 0, 0.1)
            self.assertFalse(row['measurement_available'])
            self.assertEqual(row['matched_sites'], 0)

    def test_child_launch_failure_does_not_skip_remaining_cases(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('run_benchmark.subprocess.check_output', return_value='revision'), \
             patch('run_benchmark.subprocess.run', side_effect=OSError('launch failed')) as child:
            output = Path(tmp) / 'new'
            self.assertEqual(suite.execute(output), 1)
            report = json.loads((output / 'summary.json').read_text())
            self.assertEqual(child.call_count, 20)
            self.assertEqual(report['status'], 'completed')
            self.assertEqual(report['metrics']['distinct_migration_cases'], 20)
            self.assertEqual(report['metrics']['expected_sites'], 137)
            self.assertEqual(report['metrics']['validation_passed'], 0)
            self.assertEqual(len(list(output.glob('*.log'))), 20)
            summary = (output / 'summary.md').read_text()
            self.assertEqual(summary.count('| failed |'), 20)
            self.assertNotIn('](pubsub-rename/review/index.html)', summary)

    def test_conflicting_embedded_truth_identity_is_rejected(self):
        original_read = suite.read
        def altered(path):
            result = original_read(path)
            if path.name == 'expected.json':
                result['source_revision'] = 'wrong'
            return result
        with patch('run_benchmark.read', side_effect=altered):
            with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
                suite.manifest()

    def test_readable_partial_run_keeps_pending_cases_visible(self):
        report = {'status': 'running', 'results': []}
        text = suite.render_summary(report, suite.manifest())
        self.assertEqual(text.count('| pending |'), 40)
        self.assertEqual(text.count('unmeasured/4'), 3)
        self.assertEqual(text.count('unmeasured/6'), 4)
        self.assertEqual(text.count('unmeasured/9'), 7)
        self.assertEqual(text.count('unmeasured/11'), 1)
        self.assertEqual(text.count('unmeasured/5'), 1)
        self.assertEqual(text.count('unmeasured/8'), 2)
        self.assertEqual(text.count('unmeasured/3'), 2)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, 'new directory'):
                suite.execute(Path(tmp))


if __name__ == '__main__':
    unittest.main()
