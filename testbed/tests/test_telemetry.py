"""Negative checks for the independent telemetry evaluator."""
import copy
import unittest
from testbed.telemetry.run import check_results, expected, requests


class TelemetryOracleTests(unittest.TestCase):
    def test_valid_and_boundary(self):
        wanted = expected('rename')
        check_results(wanted, wanted)
        self.assertFalse(wanted[2]['speeding'])
        self.assertTrue(wanted[3]['speeding'])
        self.assertEqual(len(requests()), 8)

    def test_wrong_units_threshold_key_or_construction_rejected(self):
        wanted = expected('rename')
        for mutation in ('units', 'threshold', 'old_key', 'construction', 'missing', 'bool'):
            actual = copy.deepcopy(wanted)
            if mutation == 'units':
                actual[1]['fields']['ground_speed_mps'] *= 3.6
            elif mutation == 'threshold':
                actual[2]['speeding'] = True
            elif mutation == 'old_key':
                actual[1]['fields']['speed_mps'] = actual[1]['fields'].pop('ground_speed_mps')
            elif mutation == 'construction':
                actual[1]['constructed_payload'] = actual[0]['constructed_payload']
            elif mutation == 'missing':
                actual.pop()
            else:
                actual[0]['speeding'] = 0
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                check_results(actual, wanted)
