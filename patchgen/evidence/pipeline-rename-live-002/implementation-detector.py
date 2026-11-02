"""Descriptor-based single-file change detection. No diagnostic-text parsing."""
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


def compare(old, new):
    """Return normalized events and unsupported changes, matched by wire identity."""
    if (old.name, old.package) != (new.name, new.package):
        return [], ['canonical file/package identity changed']
    events, unsupported = [], []
    def messages(items, prefix):
        result = {}
        for item in items:
            name = prefix + '.' + item.name
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
        if a.oneof_decl != b.oneof_decl or a.options != b.options:
            unsupported.append(name + ': message options/oneofs changed')
        for number in sorted(aa.keys() | bb.keys()):
            x, y = aa.get(number), bb.get(number)
            base = dict(message=name, field_number=number, old_name=x.name if x else None,
                        new_name=y.name if y else None)
            if x is None:
                unsupported.append(name + ': field added'); continue
            if y is None:
                events.append(dict(category='field_removed', **base)); continue
            if x.name != y.name:
                events.append(dict(category='field_renamed', **base))
            if (x.type, x.type_name) != (y.type, y.type_name):
                events.append(dict(category='field_type_changed', old_type=x.type, new_type=y.type, **base))
            if (x.label, x.HasField('oneof_index'), x.oneof_index, x.options, x.default_value) != (y.label, y.HasField('oneof_index'), y.oneof_index, y.options, y.default_value):
                unsupported.append(name + '.' + x.name + ': cardinality/oneof/options/default changed')
    def enums(file):
        result = {file.package + '.' + e.name:e for e in file.enum_type}
        for name, message in messages(file.message_type, file.package).items():
            result.update({name + '.' + e.name:e for e in message.enum_type})
        return result
    aa, bb = enums(old), enums(new)
    if aa.keys() != bb.keys():
        unsupported.append('enum declaration added/removed')
    for name in sorted(aa.keys() & bb.keys()):
        a = {(v.number,v.name) for v in aa[name].value}
        b = {(v.number,v.name) for v in bb[name].value}
        if a - b or aa[name].options != bb[name].options:
            unsupported.append(name + ': enum removal/rename/options')
        for number, value in sorted(b-a):
            events.append(dict(category='enum_value_added', enum=name, value=value, number=number))
    # Comments can carry units/frames/meaning; descriptors do not resolve that intent.
    return events, unsupported


def detect(old_schema, new_schema, schema_path, revision, change_id, intended_behavior):
    old, oh = descriptor(old_schema, schema_path)
    new, nh = descriptor(new_schema, schema_path)
    events, unsupported = compare(old, new)
    status = 'complete' if len(events) == 1 and not unsupported and intended_behavior.strip() else 'partial'
    return dict(adapter_version='1.0', producer='independent-descriptor-detector/1.0', status=status,
                source_revision=revision, old_schema_sha256=digest(old_schema), new_schema_sha256=digest(new_schema),
                old_descriptor_sha256=oh, new_descriptor_sha256=nh, events=events, unsupported=unsupported,
                semantic_policy='caller-supplied intended behavior; comments/units/frames are not inferred',
                change=dict(id=change_id, category=events[0]['category'] if len(events)==1 else 'ambiguous',
                            schema_path=schema_path, old_schema=old_schema, new_schema=new_schema),
                intended_behavior=intended_behavior)
