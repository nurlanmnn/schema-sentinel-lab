"""Descriptor-based single-file change detection. No diagnostic-text parsing."""
import copy
import hashlib
import subprocess
import tempfile
from pathlib import Path
from google.protobuf.descriptor_pb2 import FileDescriptorSet
from patchgen.adapter import digest
from patchgen.generator import ContractError, safe_path


def descriptor(schema, schema_path):
    safe_path(schema_path)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / schema_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(schema)
        (root / 'buf.yaml').write_text('version: v2\nmodules:\n  - path: .\n')
        result = subprocess.run(['buf', 'build', '--as-file-descriptor-set', '-o', 'schema.bin'],
                                cwd=root, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ContractError('descriptor build failed: ' + result.stderr)
        raw = (root / 'schema.bin').read_bytes()
        bundle = FileDescriptorSet.FromString(raw)
        files = [f for f in bundle.file if f.name == schema_path]
        if len(files) != 1:
            raise ContractError('canonical descriptor file identity missing')
        return files[0], hashlib.sha256(raw).hexdigest()


def qualified(prefix, name):
    """Protobuf names omit a leading dot even when the package is empty."""
    return prefix + "." + name if prefix else name


def field_identity(field):
    if field is None:
        return None
    return dict(name=field.name, number=field.number, type=field.type,
                type_name=field.type_name.lstrip("."), label=field.label,
                json_name=field.json_name, proto3_optional=field.proto3_optional,
                oneof_index=field.oneof_index if field.HasField("oneof_index") else None,
                default_value=field.default_value if field.HasField("default_value") else None)


def oneof_structure(message, renamed_fields):
    """Ignore a synthetic group name only when its own field is renamed."""
    members = {}
    for field in message.field:
        if field.HasField('oneof_index'):
            members.setdefault(field.oneof_index, []).append(field)
    result = []
    for index, declaration in enumerate(message.oneof_decl):
        fields = members.get(index, [])
        if len(fields) == 1 and fields[0].proto3_optional:
            field_number = fields[0].number
            if field_number in renamed_fields:
                declaration = copy.deepcopy(declaration)
                declaration.ClearField('name')
            result.append((field_number, declaration))
        else:
            result.append((None, declaration))
    return result


def explicit_presence_field(before, after, old_file, new_file):
    """Prove a single added trailing synthetic group with no other field change."""
    if old_file.syntax != 'proto3' or new_file.syntax != 'proto3':
        return None
    index = len(before.oneof_decl)
    if len(after.oneof_decl) != index + 1:
        return None
    members = [f for f in after.field if f.HasField('oneof_index') and f.oneof_index == index]
    if len(members) != 1:
        return None
    field = members[0]
    prior = next((f for f in before.field if f.number == field.number), None)
    if (prior is None or prior.HasField('proto3_optional') or prior.HasField('oneof_index')
            or not field.proto3_optional or field.label != field.LABEL_OPTIONAL
            or field.type in (field.TYPE_MESSAGE, field.TYPE_GROUP)
            or after.oneof_decl[index].HasField('options')):
        return None
    normalized = copy.deepcopy(field)
    normalized.ClearField('proto3_optional')
    normalized.ClearField('oneof_index')
    return field.number if normalized == prior else None


def compare(old, new):
    """Return normalized events and unsupported changes, matched by wire identity."""
    if (old.name, old.package) != (new.name, new.package):
        return [], ['canonical file/package identity changed']
    events, unsupported = [], []
    def messages(items, prefix):
        result = {}
        for item in items:
            name = qualified(prefix, item.name)
            result[name] = item
            result.update(messages(item.nested_type, name))
        return result
    before = messages(old.message_type, old.package)
    after = messages(new.message_type, new.package)
    if before.keys() != after.keys():
        unsupported.append('message addition/removal/rename')
    for name in sorted(before.keys() & after.keys()):
        a, b = before[name], after[name]
        aa, bb = {f.number:f for f in a.field}, {f.number:f for f in b.field}
        renamed_fields = {number for number in aa.keys() & bb.keys()
                          if aa[number].name != bb[number].name}
        presence = explicit_presence_field(a, b, old, new)
        groups = oneof_structure(b, renamed_fields)
        if presence is not None:
            groups = groups[:-1]
        if oneof_structure(a, renamed_fields) != groups or a.options != b.options:
            unsupported.append(name + ': message options/oneofs changed')
        for number in sorted(aa.keys() | bb.keys()):
            x, y = aa.get(number), bb.get(number)
            base = dict(message=name, field_number=number, old_name=x.name if x else None,
                        new_name=y.name if y else None,
                        old_field=field_identity(x), new_field=field_identity(y))
            if x is None:
                unsupported.append(name + ': field added'); continue
            if y is None:
                events.append(dict(category='field_removed', **base)); continue
            if x.name != y.name:
                rename = dict(category='field_renamed', **base)
                if (x.proto3_optional and y.proto3_optional and
                        x.HasField('oneof_index') and y.HasField('oneof_index')):
                    rename.update(old_presence_group=a.oneof_decl[x.oneof_index].name,
                                  new_presence_group=b.oneof_decl[y.oneof_index].name)
                events.append(rename)
            if (x.type, x.type_name) != (y.type, y.type_name):
                events.append(dict(category='field_type_changed', old_type=x.type, new_type=y.type,
                                   old_type_name=x.type_name.lstrip('.'), new_type_name=y.type_name.lstrip('.'), **base))
            if number == presence:
                events.append(dict(category='field_presence_added', **base))
                continue
            if (x.label, x.HasField('oneof_index'), x.oneof_index, x.options, x.default_value) != (y.label, y.HasField('oneof_index'), y.oneof_index, y.options, y.default_value):
                unsupported.append(name + '.' + x.name + ': cardinality/oneof/options/default changed')
    def enums(file):
        result = {qualified(file.package, e.name):e for e in file.enum_type}
        for name, message in messages(file.message_type, file.package).items():
            result.update({qualified(name, e.name):e for e in message.enum_type})
        return result
    aa, bb = enums(old), enums(new)
    if aa.keys() != bb.keys():
        unsupported.append('enum declaration added/removed')
    for name in sorted(aa.keys() & bb.keys()):
        a = {(v.number,v.name) for v in aa[name].value}
        b = {(v.number,v.name) for v in bb[name].value}
        if a - b or aa[name].options != bb[name].options:
            unsupported.append(name + ': enum removal/rename/options')
        old_order = [(v.number, v.name) for v in aa[name].value]
        new_order = [(v.number, v.name) for v in bb[name].value]
        if [v for v in new_order if v in a] != old_order:
            unsupported.append(name + ': enum existing value order changed')
        if old_order and new_order and old_order[0] != new_order[0]:
            unsupported.append(name + ': enum default value changed')
        for number in sorted({v[0] for v in old_order}):
            old_first = next(v for v in old_order if v[0] == number)
            new_first = next((v for v in new_order if v[0] == number), None)
            if old_first != new_first:
                unsupported.append(name + ': enum first alias changed')
        for value in sorted(a & b):
            x=next(v for v in aa[name].value if (v.number,v.name)==value)
            y=next(v for v in bb[name].value if (v.number,v.name)==value)
            if x != y:
                unsupported.append(name + ': enum value metadata changed')
        left,right=copy.deepcopy(aa[name]),copy.deepcopy(bb[name])
        left.ClearField('value');right.ClearField('value')
        if left != right:
            unsupported.append(name + ': enum declaration metadata changed')
        for number, value in sorted(b-a):
            events.append(dict(category='enum_value_added', enum=name, value=value, number=number))
    # Check the remaining descriptor structure so unrelated changes cannot silently
    # pass under a supported field event (services, imports, syntax, file options).
    left, right = copy.deepcopy(old), copy.deepcopy(new)
    for file in (left, right):
        file.ClearField('source_code_info')
        file.ClearField('message_type')
        file.ClearField('enum_type')
    if left != right:
        unsupported.append('file syntax/options/imports/services/extensions changed')
    for name in sorted(before.keys() & after.keys()):
        a, b = copy.deepcopy(before[name]), copy.deepcopy(after[name])
        # Reserved declarations may be added for deleted fields, never removed.
        if not set(a.reserved_name) <= set(b.reserved_name) or not {(r.start,r.end) for r in a.reserved_range} <= {(r.start,r.end) for r in b.reserved_range}:
            unsupported.append(name + ': reservation removed')
        old_fields = {f.number: f for f in a.field}
        new_fields = {f.number: f for f in b.field}
        retired_names = {f.name for number, f in old_fields.items()
                         if number not in new_fields or f.name != new_fields[number].name}
        removed_numbers = old_fields.keys() - new_fields.keys()
        if set(b.reserved_name) - set(a.reserved_name) - retired_names:
            unsupported.append(name + ': unrelated reserved name added')
        old_ranges = {(r.start, r.end) for r in a.reserved_range}
        for reservation in b.reserved_range:
            if (reservation.start, reservation.end) in old_ranges:
                continue
            # Compare cardinality without expanding an arbitrarily large range.
            covered = sum(reservation.start <= n < reservation.end for n in removed_numbers)
            if covered != reservation.end - reservation.start:
                unsupported.append(name + ': unrelated reserved numbers added')
        for message in (a,b):
            for key in ('field','nested_type','enum_type','reserved_name','reserved_range','oneof_decl'):
                message.ClearField(key)
        if a != b:
            unsupported.append(name + ': unsupported message structure change')
        aa = {f.number:f for f in before[name].field}
        bb = {f.number:f for f in after[name].field}
        presence = explicit_presence_field(before[name], after[name], old, new)
        for number in sorted(aa.keys() & bb.keys()):
            if number == presence:
                continue
            a, b = copy.deepcopy(aa[number]), copy.deepcopy(bb[number])
            for field in (a,b):
                for key in ('name','json_name','type','type_name'):
                    field.ClearField(key)
            if a != b:
                unsupported.append(name + ': unsupported field metadata change')
            x,y=aa[number],bb[number]
            def json_default(field):
                parts=field.name.split('_')
                return parts[0]+''.join(p[:1].upper()+p[1:] for p in parts[1:])
            custom = x.json_name not in ('',json_default(x)) or y.json_name not in ('',json_default(y))
            if x.json_name != y.json_name and (x.name == y.name or custom):
                unsupported.append(name + ': explicit JSON name changed')
    # Comments can carry units/frames/meaning; descriptors do not resolve that intent.
    return events, unsupported


def detect(old_schema, new_schema, schema_path, revision, change_id, intended_behavior):
    old, oh = descriptor(old_schema, schema_path)
    new, nh = descriptor(new_schema, schema_path)
    events, unsupported = compare(old, new)
    structural_status = ('unsupported' if unsupported else 'no_structural_change' if not events else
                         'single_supported_event' if len(events) == 1 else 'multiple_events')
    status = 'complete' if len(events) == 1 and not unsupported and intended_behavior.strip() else 'partial'
    return dict(adapter_version='1.0', producer='independent-descriptor-detector/1.1', status=status,
                structural_status=structural_status,
                analysis_issues=(['explicit intended behavior required'] if not intended_behavior.strip() else []),
                source_revision=revision, old_schema_sha256=digest(old_schema), new_schema_sha256=digest(new_schema),
                old_descriptor_sha256=oh, new_descriptor_sha256=nh, events=events, unsupported=unsupported,
                semantic_policy='caller-supplied intended behavior; comments/units/frames are not inferred',
                change=dict(id=change_id, category=events[0]['category'] if len(events)==1 else 'ambiguous',
                            schema_path=schema_path, old_schema=old_schema, new_schema=new_schema),
                intended_behavior=intended_behavior)


def matches_single_event(record, expected):
    """Match a policy's explicit constraints while permitting additive evidence."""
    events = record.get('events', [])
    return (record.get('status') == 'complete' and len(events) == 1
            and all(key in events[0] and events[0][key] == value for key, value in expected.items()))
