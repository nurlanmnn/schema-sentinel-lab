"""Independent wire expectations and exact JSON representation boundaries."""
import base64
import copy
import unittest
from testbed.inventory.run import encode, expected, check_results, requests, varint


class InventoryOracleTests(unittest.TestCase):
    def test_wire_literals(self):
        self.assertEqual(base64.b64decode(encode('A', 1)), b'\x0a\x01A\x10\x01')
        self.assertEqual(base64.b64decode(encode('', -1)), b'\x10' + b'\xff' * 9 + b'\x01')
        self.assertEqual(base64.b64decode(encode('', 1 << 53 | 1)), b'\x10\x81\x80\x80\x80\x80\x80\x80\x10')
        self.assertEqual(varint(128), b'\x80\x01')
        self.assertEqual(base64.b64decode(encode('', 0)), b'')

    def test_width_corpus_includes_signed_endpoints_and_unsafe_neighbors(self):
        quantities = {int(r['quantity']) for r in requests('width')}
        self.assertTrue({-(1 << 63), (1 << 63) - 1, (1 << 53) + 1, -(1 << 53) - 1} <= quantities)
        self.assertEqual(len(requests()), 8)
        self.assertEqual(len(requests('width')), 16)

    def test_oracle_rejects_narrowing_numbers_and_boolean_predicates(self):
        wanted = expected('width')
        for mutate in ('number', 'rounded', 'predicate', 'wire'):
            actual = copy.deepcopy(wanted)
            if mutate == 'number':
                actual[0]['fields']['quantity'] = 0
            elif mutate == 'rounded':
                actual[12]['fields']['quantity'] = str(1 << 53)
            elif mutate == 'predicate':
                actual[0]['in_stock'] = 0
            else:
                actual[0]['constructed_payload'] = 'AAAA'
            with self.assertRaises(ValueError):
                check_results(actual, wanted)

    def test_oracle_rejects_invalid_modes_and_out_of_range_integers(self):
        for value in (True, 1 << 63, -(1 << 63) - 1):
            with self.assertRaises(ValueError):
                encode('A', value)
        with self.assertRaises(ValueError):
            requests('unknown')


if __name__ == '__main__':
    unittest.main()
