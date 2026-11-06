"""Pinned Git runtime inventory with an explicit, narrow auxiliary-file policy."""
from pathlib import PurePosixPath
from patchgen.generator import command, safe_path, ContractError

LANGUAGES = {'.py': 'python', '.ts': 'typescript', '.cs': 'csharp'}
# These are build/dependency inputs, not independently scanned runtime code.
# Every other unknown file blocks completeness, including extensionless files.
AUXILIARY_NAMES = {'requirements.txt', 'package.json', 'package-lock.json', 'tsconfig.json'}


def inventory(repo, revision):
    """Return every tracked runtime entry; never follow symlinks or gitlinks."""
    raw = command(['git', 'ls-tree', '-rz', '--full-tree', revision, '--', 'runtimes/'], repo)
    entries = []
    for row in raw.split('\0'):
        if not row:
            continue
        metadata, path = row.split('\t', 1)
        mode, object_type, object_id = metadata.split(' ')
        entry = dict(path=path, mode=mode, object_type=object_type, object_id=object_id)
        try:
            safe_path(path)
        except ContractError:
            disposition = 'unsupported_path'
        else:
            if object_type != 'blob' or mode not in ('100644', '100755'):
                disposition = 'unsupported_git_entry'
            elif PurePosixPath(path).suffix in LANGUAGES:
                disposition = 'source'
                entry['language'] = LANGUAGES[PurePosixPath(path).suffix]
            elif PurePosixPath(path).name in AUXILIARY_NAMES or PurePosixPath(path).suffix == '.csproj':
                disposition = 'auxiliary'
            else:
                disposition = 'unsupported_file'
        entry['disposition'] = disposition
        entries.append(entry)
    return entries


def blocking_entries(entries):
    return [entry for entry in entries if entry['disposition'] not in ('source', 'auxiliary')]
