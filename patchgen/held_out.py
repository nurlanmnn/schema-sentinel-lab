"""Seal and verify the held-out case registry (docs/patch-generation/held-out-plan.md).

A sealed registry pins, by SHA-256, the code that runs and judges cases, every
case's fixture and reference folder, the case evidence that proves solvability
and discrimination, and the locked prompt fingerprints. An append-only ledger,
committed with the registry, records every attempt before any model request.
Held-out runs verify all of this at execution and refuse any mismatch.

Limits that code cannot enforce: evaluator independence is attested by a
person, and the external anchor is the registry digest the evaluator records
when the seal is pushed.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_VERSION = 2
LABELS = ('new_mechanism', 'transfer')
MIN_NEGATIVE_CONTROLS = 3
# Everything that builds model input, applies edits, filters feedback, generates bindings or judges patches.
HARNESS_PATTERNS = ('patchgen/*.py', 'patchgen/pipeline-requirements.txt', 'testbed/**/*.py', 'run_*.py',
                    'tools/codegen/generate.py', 'tools/codegen/package.json', 'tools/codegen/package-lock.json',
                    'buf.gen.yaml', 'buf.yaml')
TRUSTED_REMOTES = ('https://github.com/', 'git@github.com:')
LEDGER = 'attempts.jsonl'
EVIDENCE_SKIP = {'workspace', 'source', 'node_modules', '.venv', 'bin', 'obj', '__pycache__'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root, name):
    path = root/name
    # Symlinks could point a sealed name at different content later.
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f'sealed path must be a regular file inside the repository: {name}')
    return path


def harness_files(root):
    return sorted({str(path.relative_to(root)) for pattern in HARNESS_PATTERNS for path in root.glob(pattern)
                   if path.is_file() and '__pycache__' not in path.parts})


def case_files(root, case):
    """Fixture, whole reference folder and listed evidence: computed, so nothing required can be omitted."""
    reference = root/'patchgen/reference'/case['profile']
    files = {f"patchgen/fixtures/{case['profile']}/runtime-input.json"}
    files |= {str(p.relative_to(root)) for p in reference.rglob('*') if p.is_file()} if reference.is_dir() else set()
    files |= set(case['negative_controls']) | {case['reference_evidence'], *case['control_evidence']}
    return sorted(files)


def read_json(root, name):
    try:return json.loads(safe_file(root, name).read_text())
    except ValueError as error:raise ValueError(f'{name}: {error}') from None


def check_draft(draft, root=ROOT, *, check_evidence=True):
    """Structure every case needs before sealing, so gaps surface before hashes are computed."""
    if not isinstance(draft, dict) or not isinstance(draft.get('evaluator'), dict) or not draft['evaluator'].get('name'):
        raise ValueError('registry needs an independent evaluator name')
    cases = draft.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('registry needs at least one case')
    by_id = {}
    for case in cases:
        for key in ('id', 'case', 'label', 'status', 'approved_by', 'approved_on'):
            if not isinstance(case.get(key), str) or not case[key]:
                raise ValueError(f"case {case.get('id')}: missing {key}")
        if case['id'] in by_id or case['case'] in {c['case'] for c in by_id.values()}:
            raise ValueError(f"duplicate case id or name: {case['id']}")
        by_id[case['id']] = case
        if case['label'] not in LABELS:raise ValueError(f"case {case['id']}: label must be one of {LABELS}")
        if case['status'] == 'withdrawn':
            # Withdrawn cases stay in every denominator and must say why.
            if not case.get('withdrawn_reason'):raise ValueError(f"case {case['id']}: withdrawn without a reason")
            continue
        if case['status'] != 'sealed':raise ValueError(f"case {case['id']}: status must be sealed or withdrawn")
        if not isinstance(case.get('profile'), str) or not case['profile'] or '/' in case['profile']:
            raise ValueError(f"case {case['id']}: missing fixture profile")
        controls, evidence = case.get('negative_controls'), case.get('control_evidence')
        if (not isinstance(controls, list) or len(set(controls)) < MIN_NEGATIVE_CONTROLS or len(set(controls)) != len(controls)
                or not isinstance(evidence, list) or len(evidence) != len(controls) or len(set(evidence)) != len(evidence)
                or not isinstance(case.get('reference_evidence'), str)):
            raise ValueError(f"case {case['id']}: needs {MIN_NEGATIVE_CONTROLS}+ distinct negative controls, one rejection "
                             'evidence file per control, and reference_evidence')
        if check_evidence:
            # The reference patch must pass every check, and each wrong patch must be rejected.
            if read_json(root, case['reference_evidence']).get('status') != 'validation_passed':
                raise ValueError(f"case {case['id']}: reference evidence does not show validation_passed")
            for name in evidence:
                if read_json(root, name).get('status') not in ('failed', 'rejected'):
                    raise ValueError(f"case {case['id']}: control evidence {name} does not show a rejection")
    for case in cases:
        parent = case.get('variant_of')
        if parent and (parent == case['id'] or parent not in by_id or by_id[parent].get('variant_of')
                       or by_id[parent]['status'] != 'sealed'):
            raise ValueError(f"case {case['id']}: variant parent must be a different sealed, non-variant case")
    return draft


def seal(draft_path, output, root=ROOT):
    """Turn an approved draft into a registry with hashes, plus an empty attempt ledger."""
    from patchgen.live_suite import LOCKED_DECISION, prompt_fingerprints
    draft = check_draft(json.loads(Path(draft_path).read_text()), root)
    output = Path(output)
    if output.exists() or (output.parent/LEDGER).exists():
        raise ValueError('registry already exists; a sealed registry is never overwritten')
    registry = dict(registry_version=REGISTRY_VERSION, status='sealed',
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        evaluator=draft['evaluator'], locked_configuration=LOCKED_DECISION, prompt_fingerprints=prompt_fingerprints(),
        harness_sha256={name: digest(safe_file(root, name)) for name in harness_files(root)}, cases=[])
    for case in draft['cases']:
        sealed = dict(case)
        if case['status'] == 'sealed':
            fixture = read_json(root, f"patchgen/fixtures/{case['profile']}/runtime-input.json")
            sealed.update(source_revision=fixture['source_revision'],
                          files={name: digest(safe_file(root, name)) for name in case_files(root, case)})
        registry['cases'].append(sealed)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(registry, indent=2) + '\n')
    (output.parent/LEDGER).write_text('')
    return registry


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)


def require_append_only(root, relative):
    """Every committed version of the ledger must extend the one before it."""
    commits = git(root, 'log', '--reverse', '--format=%H', '--', relative).stdout.split()
    if not commits:raise ValueError('attempt ledger must be committed with the registry')
    previous = ''
    for commit in commits:
        text = git(root, 'show', f'{commit}:{relative}').stdout
        if not text.startswith(previous):raise ValueError('attempt ledger history was rewritten; attempts cannot be removed')
        previous = text


def verify(registry_path, root=ROOT, *, require_git=True, trusted_remotes=TRUSTED_REMOTES):
    """Return the registry if every pinned hash still matches; raise ValueError otherwise."""
    from patchgen.live_suite import LOCKED_DECISION, prompt_fingerprints
    root = Path(root)
    registry_path = Path(registry_path)
    if registry_path.is_symlink():raise ValueError('registry must not be a symlink')
    registry = json.loads(registry_path.read_text())
    if registry.get('registry_version') != REGISTRY_VERSION or registry.get('status') != 'sealed':
        raise ValueError('held-out registry is not a sealed version-2 registry')
    check_draft(registry, root, check_evidence=False)
    if registry.get('locked_configuration') != LOCKED_DECISION or registry.get('prompt_fingerprints') != prompt_fingerprints():
        raise ValueError('locked configuration or prompts changed after sealing')
    pinned = registry.get('harness_sha256') or {}
    if set(pinned) != set(harness_files(root)):
        raise ValueError('harness file set changed after sealing')
    changed = [name for name, value in pinned.items() if digest(safe_file(root, name)) != value]
    for case in registry['cases']:
        if case['status'] == 'sealed':
            if set(case['files']) != set(case_files(root, case)):
                changed.append(f"{case['id']} file set")
            changed += [name for name, value in case['files'].items() if (root/name).is_file() and digest(safe_file(root, name)) != value]
    if changed:
        raise ValueError('sealed files changed: ' + ', '.join(sorted(changed)))
    # Evidence still says what it said when sealed; recheck its content, not only its hash.
    check_draft(registry, root)
    if require_git:
        relative = str(registry_path.resolve().relative_to(root.resolve()))
        ledger = str(Path(relative).parent/LEDGER)
        for case in registry['cases']:
            if case['status'] == 'sealed' and git(root, 'cat-file', '-e', case['source_revision'] + '^{commit}').returncode:
                raise ValueError(f"case {case['id']}: source revision is not a commit in this repository")
        # Tracked edits could alter behaviour without touching a pinned file.
        if git(root, 'diff', '--quiet', 'HEAD').returncode != 0:
            raise ValueError('tracked files have uncommitted changes (including the attempt ledger); commit before a held-out run')
        added = git(root, 'log', '--format=%H', '--', relative).stdout.split()
        if len(added) != 1:
            raise ValueError('sealed registry must be committed exactly once and never modified')
        upstream = git(root, 'rev-parse', '--abbrev-ref', '@{upstream}').stdout.strip()
        url = git(root, 'remote', 'get-url', upstream.split('/')[0]).stdout.strip() if upstream else ''
        if not url.startswith(trusted_remotes):
            raise ValueError('upstream must be a GitHub remote so the seal has an external timestamp')
        if git(root, 'merge-base', '--is-ancestor', added[0], '@{upstream}').returncode != 0:
            raise ValueError('sealed registry must be pushed to the upstream branch before the run')
        require_append_only(root, ledger)
    return registry


def registry_sha256(registry_path):
    return digest(Path(registry_path))


def ledger_entries(registry_path):
    path = Path(registry_path).parent/LEDGER
    if not path.is_file():raise ValueError('attempt ledger is missing; it is created by seal and must be committed')
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def evidence_sha256(directory):
    """Digest of retained evidence a later repair reads, excluding ignored worktrees and installs."""
    directory = Path(directory)
    rows = []
    for path in sorted(directory.rglob('*')):
        relative = path.relative_to(directory)
        if path.is_file() and not path.is_symlink() and not EVIDENCE_SKIP & set(relative.parts):
            rows.append(f'{relative}\t{digest(path)}')
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()


def record(registry_path, entry):
    """Append atomically under an exclusive lock so concurrent attempts are serialized."""
    lock = Path(registry_path).parent/'.attempt.lock'
    try:fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:raise ValueError(f'another held-out attempt is starting; remove {lock} only if none is') from None
    try:
        entries = ledger_entries(registry_path)
        entry = dict(entry, attempt=len(entries) + 1, registry_sha256=registry_sha256(registry_path),
                     at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
        # The check sees the ledger inside the lock and may add fields derived from it.
        check = entry.pop('check', None)
        entry.update((check(entries) if check else None) or {})
        with (Path(registry_path).parent/LEDGER).open('a') as ledger:
            ledger.write(json.dumps(entry, sort_keys=True) + '\n')
        return entry
    finally:
        os.close(fd); lock.unlink()


def begin_one_shot(registry_path, output, rerun_reason=None):
    def check(entries):
        previous = [e for e in entries if e['kind'] == 'one_shot']
        if previous and not rerun_reason:
            raise ValueError(f"held-out cases were already attempted (attempt {previous[0]['attempt']}); the first attempt is "
                             'the score. Pass --rerun-reason to record a separate rerun.')
    return record(registry_path, dict(kind='one_shot', output=str(Path(output).resolve()), rerun_reason=rerun_reason, check=check))


def finish(registry_path, attempt, output):
    return record(registry_path, dict(kind='completed', of_attempt=attempt, output=str(Path(output).resolve()),
                                      evidence_sha256=evidence_sha256(output)))


def begin_repair(registry_path, source, output):
    """One repair per one-shot attempt, on evidence identical to what that attempt recorded."""
    source = str(Path(source).resolve())
    def check(entries):
        done = [e for e in entries if e['kind'] == 'completed' and e['output'] == source]
        if not done:raise ValueError('repair source is not a completed held-out attempt in the ledger')
        if evidence_sha256(source) != done[-1]['evidence_sha256']:
            raise ValueError('repair source evidence changed after its attempt completed')
        if any(e['kind'] == 'repair' and e['of_attempt'] == done[-1]['of_attempt'] for e in entries):
            raise ValueError('this held-out attempt was already repaired; the repair budget is used')
        return dict(of_attempt=done[-1]['of_attempt'])
    return record(registry_path, dict(kind='repair', output=str(output), source=source, check=check))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    seal_parser = sub.add_parser('seal', help='hash an approved draft into a new registry and empty ledger')
    seal_parser.add_argument('--draft', type=Path, required=True)
    seal_parser.add_argument('--output', type=Path, default=ROOT/'held-out/registry.json')
    verify_parser = sub.add_parser('verify', help='check a sealed registry without running a model')
    verify_parser.add_argument('--registry', type=Path, default=ROOT/'held-out/registry.json')
    args = parser.parse_args()
    try:
        if args.command == 'seal':
            registry = seal(args.draft, args.output)
            print(f"Sealed {sum(c['status'] == 'sealed' for c in registry['cases'])} cases. Commit the registry and "
                  f'{LEDGER} together, push, and send this digest to the evaluator: {registry_sha256(args.output)}')
        else:
            registry = verify(args.registry)
            print(f"Registry verified ({registry_sha256(args.registry)}): "
                  f"{sum(c['status'] == 'sealed' for c in registry['cases'])} sealed cases; "
                  f"ledger attempts: {len(ledger_entries(args.registry))}")
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':raise SystemExit(main())
