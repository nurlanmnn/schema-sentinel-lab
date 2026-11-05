"""Keep the live cohort distinct from deterministic benchmark results."""
import unittest

from patchgen.live_suite import benchmark_plan
from run_benchmark import manifest


class LiveBenchmarkPlanTests(unittest.TestCase):
    def test_all_cases_are_accounted_for_without_counting_pinned_migrations(self):
        plan = benchmark_plan(manifest())
        self.assertEqual(len(plan), 20)
        self.assertEqual(list(plan.values()).count('eligible'), 8)
        self.assertEqual(list(plan.values()).count('schema_only'), 3)
        self.assertEqual(list(plan.values()).count('requires_pinned_policy'), 9)
        self.assertEqual(plan['telemetry-quantized'], 'eligible')
        self.assertEqual(plan['inventory-routing-oneof'], 'requires_pinned_policy')
