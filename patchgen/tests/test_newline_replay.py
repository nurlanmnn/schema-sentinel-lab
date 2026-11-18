"""Pure normalization checks: no network, subprocesses, or ports."""
import copy
import unittest

from patchgen.anchor_edits import resolve
from patchgen.generator import ContractError
from patchgen.newline_replay import normalize_response


class NewlineReplayTests(unittest.TestCase):
    def test_only_missing_terminal_lf_changes_and_input_is_preserved(self):
        value = dict(outcome='patch', rationale='keep me', confidence=0.9, assumptions=['unchanged'],
            candidate_reviews={'C001': {'decision': 'edit', 'reason': 'migration'}}, edits=[
                dict(before='  old\n  tail', after='  new\n  tail'),
                dict(before='remove', after=''),
                dict(before='ready\n', after='ready too\n'),
                dict(before='x\r', after='y\r'),
                dict(before=None, after=7), dict(before='', after='')])
        original = copy.deepcopy(value)
        actual, changes = normalize_response(value)
        expected = copy.deepcopy(value)
        expected['edits'][0] = dict(before='  old\n  tail\n', after='  new\n  tail\n')
        expected['edits'][1]['before'] += '\n'
        expected['edits'][3] = dict(before='x\r\n', after='y\r\n')
        self.assertEqual(actual, expected)
        self.assertEqual(value, original)
        self.assertEqual(changes, [dict(edit_index=0, appended_lf_to=['before', 'after']),
            dict(edit_index=1, appended_lf_to=['before']), dict(edit_index=3, appended_lf_to=['before', 'after'])])
        self.assertEqual(normalize_response(actual), (actual, []))

    def test_complete_lines_become_resolvable_but_partial_lines_still_fail(self):
        source = 'def f():\n    old = 1\n    return old\n'
        inventory = {'C001': dict(line=2, text='    old = 1\n')}
        positions = [dict(start_line=2, end_line=2)]
        value = dict(outcome='patch', rationale='rename', confidence=0.9, assumptions=[],
            candidate_reviews={'C001': dict(decision='edit', reason='rename')},
            edits=[dict(before='    old = 1', after='    new = 1')])
        # Since decision 0044 the live resolver accepts this directly, identically to the replay.
        self.assertEqual(resolve(source, value, inventory, positions),
                         'def f():\n    new = 1\n    return old\n')
        normalized, _ = normalize_response(value)
        self.assertEqual(resolve(source, normalized, inventory, positions),
                         'def f():\n    new = 1\n    return old\n')
        value['edits'][0]['before'] = '    old'
        normalized, _ = normalize_response(value)
        with self.assertRaisesRegex(ContractError, 'before must match exactly once'):
            resolve(source, normalized, inventory, positions)

    def test_malformed_response_is_not_repaired(self):
        for value in (None, [], {}, {'edits': 'bad'}, {'edits': [None]}):
            self.assertEqual(normalize_response(value), (value, []))


if __name__ == '__main__':
    unittest.main()
