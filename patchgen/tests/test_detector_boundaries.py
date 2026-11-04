"""Descriptor regressions for wire identity, defaults and hidden companion edits."""
import copy
import unittest
from patchgen.detector import compare, descriptor, detect
from patchgen.locator import enum_symbols


def build(text):
    return descriptor(text, 'model.proto')[0]


class DescriptorBoundaryTests(unittest.TestCase):
    def test_package_less_field_identity(self):
        old = 'syntax="proto3"; message Packet { string label=1; }'
        result = detect(old, old.replace('label=', 'caption='), 'model.proto', 'a'*40, 'rename', 'Rename label')
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['events'][0]['message'], 'Packet')
        self.assertEqual(result['events'][0]['old_field']['type'], 9)

    def test_package_less_enum_and_consumer_identity(self):
        old = 'syntax="proto3"; enum State { UNKNOWN=0; } message Packet { State state=1; }'
        record = detect(old, old.replace('UNKNOWN=0;', 'UNKNOWN=0; ACTIVE=1;'), 'model.proto', 'a'*40, 'enum', 'Add state')
        self.assertEqual(record['events'][0]['enum'], 'State')
        self.assertEqual(enum_symbols(record)['fields'][0]['message'], 'Packet')

    def test_proto2_reorder_changes_implicit_default(self):
        old = build('syntax="proto2"; enum State { READY=1; STOPPED=2; }')
        new = build('syntax="proto2"; enum State { STOPPED=2; READY=1; }')
        events, issues = compare(old, new)
        self.assertFalse(events)
        self.assertTrue(any('default' in issue for issue in issues))

    def test_new_proto2_first_value_is_not_safe_addition(self):
        old = build('syntax="proto2"; enum State { READY=1; }')
        new = build('syntax="proto2"; enum State { UNKNOWN=0; READY=1; }')
        self.assertTrue(any('default' in issue for issue in compare(old, new)[1]))

    def test_alias_order_affects_number_to_name(self):
        old = build('syntax="proto3"; enum State { option allow_alias=true; UNKNOWN=0; READY=1; ACTIVE=1; }')
        new = build('syntax="proto3"; enum State { option allow_alias=true; UNKNOWN=0; ACTIVE=1; READY=1; }')
        self.assertTrue(any('first alias' in issue for issue in compare(old, new)[1]))

    def test_alias_inserted_before_existing_name(self):
        old = build('syntax="proto3"; enum State { option allow_alias=true; UNKNOWN=0; READY=1; ACTIVE=1; }')
        new = build('syntax="proto3"; enum State { option allow_alias=true; UNKNOWN=0; NEW=1; READY=1; ACTIVE=1; }')
        self.assertTrue(compare(old, new)[1])

    def test_append_alias_retains_existing_default_and_first_alias(self):
        old = build('syntax="proto3"; enum State { option allow_alias=true; UNKNOWN=0; READY=1; ACTIVE=1; }')
        new = build('syntax="proto3"; enum State { option allow_alias=true; UNKNOWN=0; READY=1; ACTIVE=1; NEW=1; }')
        events, issues = compare(old, new)
        self.assertEqual(events[0]['value'], 'NEW')
        self.assertFalse(issues)

    def test_same_wire_kind_different_message_identity(self):
        old = build('syntax="proto3"; package demo; message A {} message B {} message Packet { A child=1; }')
        new = build('syntax="proto3"; package demo; message A {} message B {} message Packet { B child=1; }')
        event = compare(old, new)[0][0]
        self.assertEqual((event['old_type'], event['new_type']), (11, 11))
        self.assertEqual((event['old_type_name'], event['new_type_name']), ('demo.A', 'demo.B'))

    def test_companion_changes_cannot_hide_behind_rename(self):
        old = build('syntax="proto3"; package demo; message Packet { string label=1; } enum State { UNKNOWN=0; READY=1; ACTIVE=2; }')
        for mutation in ('service', 'extension', 'json', 'presence', 'enum_order', 'reserved'):
            new = copy.deepcopy(old)
            new.message_type[0].field[0].name = 'caption'
            if mutation == 'service': new.service.add(name='API')
            elif mutation == 'extension': new.message_type[0].extension_range.add(start=100, end=101)
            elif mutation == 'json': new.message_type[0].field[0].json_name = 'custom'
            elif mutation == 'presence': new.message_type[0].field[0].proto3_optional = True
            elif mutation == 'enum_order':
                new.enum_type[0].value.reverse()
            else:
                old.message_type[0].reserved_name.append('retired')
            with self.subTest(mutation=mutation):
                self.assertTrue(compare(old, new)[1])

    def test_reservations_only_track_retired_fields(self):
        old = build('syntax="proto3"; message Packet { string label=1; int32 count=2; }')
        safe = build('syntax="proto3"; message Packet { reserved 1; reserved "label"; int32 count=2; }')
        self.assertFalse(compare(old, safe)[1])
        unsafe = build('syntax="proto3"; message Packet { reserved 1 to 100; reserved "label", "unrelated"; }')
        self.assertTrue(any('unrelated reserved' in issue for issue in compare(old, unsafe)[1]))
        rename = build('syntax="proto3"; message Packet { reserved "label"; string caption=1; int32 count=2; }')
        self.assertFalse(compare(old, rename)[1])

    def test_no_structural_change_is_explicit_and_not_exportable(self):
        old = 'syntax="proto3"; message Packet { string label=1; }'
        record = detect(old, '// units changed\n'+old, 'model.proto', 'a'*40, 'meaning', 'Changed meaning')
        self.assertEqual(record['structural_status'], 'no_structural_change')
        self.assertEqual(record['status'], 'partial')
        self.assertFalse(record['events'])

    def test_optional_field_rename_preserves_synthetic_oneof_identity(self):
        old = 'syntax="proto3"; message Packet { optional string label=1; string _label=2; }'
        record = detect(old, old.replace('string label=', 'string caption='), 'model.proto', 'a'*40, 'rename', 'Keep optional presence')
        self.assertEqual(record['status'], 'complete')
        self.assertEqual([e['category'] for e in record['events']], ['field_renamed'])
        self.assertTrue(record['events'][0]['new_field']['proto3_optional'])
        self.assertEqual(record['events'][0]['old_presence_group'], 'X_label')
        self.assertEqual(record['events'][0]['new_presence_group'], '_caption')

    def test_real_oneof_rename_still_blocks_a_field_rename(self):
        old = build('syntax="proto3"; message Packet { oneof group { string label=1; } }')
        new = build('syntax="proto3"; message Packet { oneof other { string caption=1; } }')
        self.assertTrue(any('oneofs' in issue for issue in compare(old, new)[1]))

    def test_unrelated_rename_cannot_hide_changed_presence_group(self):
        old = 'syntax="proto3"; message Packet { optional string label=1; string other=2; }'
        new = old.replace('other=', '_label=')
        record = detect(old, new, 'model.proto', 'a'*40, 'rename', 'Rename only the second field')
        self.assertEqual(record['status'], 'partial')
        self.assertTrue(any('oneofs' in issue for issue in record['unsupported']))

    def test_clean_implicit_scalar_to_optional_keeps_existing_oneofs(self):
        old = build('syntax="proto3"; message Packet { oneof group { string name=1; } optional string code=2; int32 count=3; }')
        new = build('syntax="proto3"; message Packet { oneof group { string name=1; } optional string code=2; optional int32 count=3; }')
        events, issues = compare(old, new)
        self.assertFalse(issues)
        self.assertEqual([e['category'] for e in events], ['field_presence_added'])
        self.assertFalse(events[0]['old_field']['proto3_optional'])
        self.assertTrue(events[0]['new_field']['proto3_optional'])
        for mutation in ('group_options', 'real_group', 'second_member', 'field_metadata'):
            changed = copy.deepcopy(new)
            message = changed.message_type[0]
            if mutation == 'group_options':
                message.oneof_decl[-1].options.SetInParent()
            elif mutation == 'real_group':
                message.oneof_decl[0].name = 'other'
            elif mutation == 'second_member':
                message.field[0].oneof_index = message.field[-1].oneof_index
            else:
                message.field[-1].json_name = 'custom'
            with self.subTest(mutation=mutation):
                self.assertTrue(compare(old, changed)[1])
        self.assertTrue(compare(new, old)[1])
