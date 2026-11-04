"""Prepare a clean participant kit or evaluate a submitted telemetry migration."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import run_demo
from patchgen.generator import (
    ContractError, apply_and_validate, check_patch, command, load_validation_profile, save,
)

ROOT = run_demo.ROOT
CASE = 'telemetry-units'
PROFILE = run_demo.CASES[CASE][0]
FIXTURE = ROOT / 'patchgen/fixtures' / PROFILE / 'runtime-input.json'
KIT_PATHS = ('proto', 'runtimes', 'generated', 'buf.yaml', 'buf.gen.yaml', '.gitignore', '.gitattributes')
LANGUAGES = {'.cs': 'csharp', '.py': 'python', '.ts': 'typescript'}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(output):
    fixture = json.loads(FIXTURE.read_text())
    revision = fixture['source_revision']
    output = run_demo.check_output(output)
    output.mkdir(parents=True)
    archive = output / 'source.zip'
    command(['git', 'archive', '--format=zip', '-o', str(archive), revision, *KIT_PATHS], ROOT)
    change = fixture['change']
    (output / 'SETUP.md').write_text("""# Participant setup

Extract source.zip into an empty directory. Open a shell in the extracted
directory and initialize a new Git repository. Commit the extracted files as
your baseline before editing. Prepare Git, Buf, Python 3.13, Node.js 22 or
newer, and the .NET 8 SDK. Use the dependency declarations in runtimes/ to
set up the three languages before starting the task.

Open TASK.md when you are ready to start timing.
""")
    (output / 'TASK.md').write_text(f"""# Telemetry migration

Source revision `{revision}`. Start timing now, before reading the migration
requirements. Use an editor and ordinary local CLI tools. Work independently
of AI assistance, prior solutions, and other participants. Pause for unrelated
interruptions. Include time spent reading, editing, and running local checks.
Stop timing when your first submission is ready. Record active elapsed seconds.

{fixture['intended_behavior']}

Apply this exact target schema in `{change['schema_path']}`.

```proto
{change['new_schema'].rstrip()}
```

Submit edits to existing runtime source files and the target schema.
If you regenerate bindings locally, leave those out of the submission.
With Buf installed, `buf generate` can regenerate bindings for local builds.
Runtime dependency declarations are included in the source archive.

From the extracted source root, export the patch to a file outside the source
tree using `git diff --no-ext-diff --no-color HEAD -- proto runtimes`.
Give the evaluator the patch and your elapsed seconds. Tell the evaluator
if you saw the solution before the task or departed from the timing protocol.
""")
    save(output / 'manifest.json', dict(case=CASE, source_revision=revision,
                                       source_sha256=sha256(archive), task_sha256=sha256(output / 'TASK.md'),
                                       setup_sha256=sha256(output / 'SETUP.md')))


def runtime_scope(case):
    revision = case['source_revision']
    files = command(['git', 'ls-tree', '-r', '--name-only', revision, '--', 'runtimes'], ROOT)
    case['affected_files'] = [
        dict(path=path, language=LANGUAGES[Path(path).suffix],
             source_context=command(['git', 'show', f'{revision}:{path}'], ROOT))
        for path in files.splitlines() if Path(path).suffix in LANGUAGES
    ]
    return {file['path'] for file in case['affected_files']} | {case['change']['schema_path']}


def verify_patch(patch, case, allowed):
    check_patch(patch.read_text(), case)
    stats = command(['git', 'apply', '--numstat', '-z', str(patch)], ROOT)
    for entry in stats.rstrip('\0').split('\0'):
        fields = entry.split('\t', 2)
        if len(fields) != 3 or fields[2] not in allowed:
            raise ContractError('Git parsed a patch path outside the submission scope')


def evaluate(patch, output, kind, elapsed):
    if kind == 'human_submission':
        if elapsed is None or not math.isfinite(elapsed) or elapsed <= 0:
            raise ContractError('Human submissions require positive, finite elapsed seconds.')
    elif elapsed is not None:
        raise ContractError('Synthetic dry runs cannot record human elapsed seconds.')
    diff = patch.read_bytes()
    output = run_demo.check_output(output)
    output.mkdir(parents=True)
    submission = output / 'submission.patch'
    submission.write_bytes(diff)
    report = dict(status='rejected', mode=kind, case=CASE,
                  self_reported_active_seconds=elapsed, human_review_seconds=None,
                  human_approval_required=True, model_requests=0,
                  submission_sha256=sha256(submission), fixture_sha256=sha256(FIXTURE),
                  evaluator_revision=command(['git', 'rev-parse', 'HEAD'], ROOT).strip(),
                  evaluator_sha256=sha256(Path(__file__)),
                  validator_sha256=sha256(ROOT / 'patchgen/generator.py'))
    source = output / 'source'
    workspace = output / 'workspace'
    started = time.monotonic()
    try:
        case = run_demo.preflight(CASE, source)
        report['source_revision'] = case['source_revision']
        verify_patch(submission, case, runtime_scope(case))
        profile = load_validation_profile(case, PROFILE)
        oracle = output / 'telemetry-oracle-source.py'
        oracle.write_bytes((ROOT / 'testbed/telemetry/run.py').read_bytes())
        report['oracle_sha256'] = sha256(oracle)
        command(['git', 'worktree', 'add', '--detach', str(source), case['source_revision']], ROOT)
        report['status'] = 'validation_failed'
        apply_and_validate(source, case, {'diff': submission.read_text()}, output,
                           run_checks=True, validation_profile=profile, local_codegen=True)
        report['runtime_validation'] = json.loads((output / 'telemetry/report.json').read_text())
        report['status'] = 'validation_passed'
    except (OSError, ValueError, RuntimeError, SyntaxError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    finally:
        report['evaluator_seconds'] = time.monotonic() - started
        for tree in (workspace, source):
            if (tree / '.git').is_file():
                try:
                    command(['git', 'worktree', 'remove', '--force', str(tree)], ROOT)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    report.setdefault('cleanup_errors', []).append(str(error))
        save(output / 'report.json', report)
    print(json.dumps(report, indent=2))
    return int(report['status'] != 'validation_passed' or bool(report.get('cleanup_errors')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    kit = actions.add_parser('prepare')
    kit.add_argument('--output', type=Path, required=True)
    grade = actions.add_parser('evaluate')
    grade.add_argument('--output', type=Path, required=True)
    grade.add_argument('--patch', type=Path, required=True)
    grade.add_argument('--kind', choices=('human_submission', 'synthetic_dry_run'), required=True)
    grade.add_argument('--elapsed-seconds', type=float)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            prepare(args.output)
            return 0
        return evaluate(args.patch, args.output, args.kind, args.elapsed_seconds)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
