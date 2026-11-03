"""Dispatch bounded positive evidence under declared generated-module policies."""
from patchgen.python_bindings import POLICY as PYTHON_POLICY, references as python_references
from patchgen.typescript_bindings import POLICY as TYPESCRIPT_POLICY, references as typescript_references, runtime_field_name


def analyze_bindings(text, language, event, schema_path, source_path, python_policy=None, typescript_policy=None):
    if not event or not event.get('old_name'):
        return [], []
    identity = (schema_path, event.get('message'))
    if language == 'python':
        policy = python_policy or PYTHON_POLICY.get(identity)
        return python_references(text, event['old_name'], *policy) if policy else ([], [])
    if language == 'typescript':
        policy = typescript_policy or TYPESCRIPT_POLICY.get(identity)
        if policy and not source_path:
            return [], ['source path required for ts-proto import identity']
        if not policy:
            return [], []
        refs, issues = typescript_references(text, event['old_name'], *policy, source_path)
        if event['category'] == 'field_renamed' and runtime_field_name(event.get('new_name')) is None:
            issues.append('new ts-proto member naming outside declared policy; edit requirement unresolved')
        return refs, issues
    return [], []


def reference_requires_edit(language, event):
    """Require edits only when a supported runtime member changes/disappears.

    Receiver evidence and source-member migration are distinct. A protobuf rename
    can preserve ts-proto's generated camel-case member. Unknown mappings remain
    review candidates; this function never establishes message identity.
    """
    if not event:
        return False
    if event['category'] == 'field_removed':
        return True
    if event['category'] != 'field_renamed':
        return False
    if language == 'typescript':
        old = runtime_field_name(event.get('old_name'))
        new = runtime_field_name(event.get('new_name'))
        return old is not None and new is not None and old != new
    return language == 'python'
