"""Dispatch bounded positive evidence under declared generated-module policies."""
from patchgen.python_bindings import POLICY as PYTHON_POLICY, references as python_references
from patchgen.typescript_bindings import POLICY as TYPESCRIPT_POLICY, references as typescript_references


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
        return typescript_references(text, event['old_name'], *policy, source_path) if policy else ([], [])
    return [], []
