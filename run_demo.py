"""Bootstrap the bounded independent demo; never approve or merge a proposal."""
import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CASES = {
    'removal': ('entity-name-removal', 'deterministic_remove_name_v1'),
    'rename': ('entity-name-rename', 'deterministic_rename_roles'),
    'utf8': ('v2-identifier-bytes', 'deterministic_utf8_v2'),
}


def check_output(output):
    output = output.resolve()
    if output.exists():
        raise RuntimeError('Output must be a new directory; retained runs are never overwritten.')
    # Never put the implementation checkout inside a newly created evidence root.
    if output == ROOT or ROOT.is_relative_to(output):
        raise RuntimeError('Output cannot contain the implementation checkout.')
    return output


def preflight(case, output):
    check_output(output)
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError('This reproducibility demo requires Python 3.13 (the tested analysis environment).')
    from run_local import check_tools
    check_tools()
    for tool in ('git', 'buf'):
        if not shutil.which(tool):
            raise RuntimeError(f'Missing {tool} on PATH. See docs/patch-generation/demo.md.')
    fixture = json.loads((ROOT / 'patchgen/fixtures' / CASES[case][0] / 'runtime-input.json').read_text())
    revision = fixture['source_revision']
    found = subprocess.run(['git', 'cat-file', '-e', revision + '^{commit}'], cwd=ROOT,
                           capture_output=True)
    if found.returncode:
        raise RuntimeError('Pinned testbed commit is absent. Use a full clone, or fetch full history before rerunning.')
    for port in (8000, 8001, 8002):
        with socket.socket() as probe:
            # Match the runtime servers: completed connections in TIME_WAIT do
            # not mean a listener is still active after a successful prior run.
            if sys.platform != 'win32':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError as error:
                raise RuntimeError(f'Port {port} is unavailable; stop its current service before running.') from error
    return fixture


def execute(case, output):
    output = check_output(output)
    fixture = preflight(case, output)
    output.mkdir(parents=True)
    python = ROOT / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    started = time.monotonic()
    report = {'status': 'failed', 'case': case, 'source_revision': fixture['source_revision'],
              'mode': 'deterministic_proposal', 'model_requests': 0, 'human_approval_required': True,
              'timing_scope': 'bootstrap plus local pipeline; not propagation or human review time'}
    try:
        with (output / 'demo.log').open('w') as log:
            def run(args):
                log.write('$ ' + subprocess.list2cmdline([str(x) for x in args]) + '\n')
                log.flush()
                subprocess.run([str(x) for x in args], cwd=ROOT, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
            report['implementation_revision'] = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            report['tools'] = {tool: subprocess.check_output([tool, '--version'], cwd=ROOT, text=True).strip()
                               for tool in ('git', 'buf', 'node', 'npm', 'dotnet')}
            report['bootstrap_python'] = sys.version
            if not python.exists():
                run([sys.executable, '-m', 'venv', ROOT / '.venv'])
            environment_version = subprocess.check_output([str(python), '--version'], cwd=ROOT, text=True).strip()
            report['analysis_python'] = environment_version
            if not environment_version.startswith('Python 3.13.'):
                raise RuntimeError('Existing .venv must use Python 3.13; choose a fresh clone or recreate that environment before running.')
            run([python, '-m', 'pip', 'install', '-r', ROOT / 'patchgen/pipeline-requirements.txt'])
            run([python, '-m', 'patchgen.pipeline', '--fixture',
                 ROOT / 'patchgen/fixtures' / CASES[case][0] / 'runtime-input.json',
                 '--output', output / 'run', '--generate', '--strategy', CASES[case][1],
                 '--review-output', output / 'review'])
            pipeline = json.loads((output / 'run/report.json').read_text())
            if pipeline['status'] != 'validation_passed' or not (output / 'review/index.html').is_file():
                raise RuntimeError('Demo did not produce a validated proposal and review bundle.')
            report['status'] = 'validation_passed'
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        (output / 'demo-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print(f"Details: {output / 'demo.log'}")
    if report['status'] == 'validation_passed':
        print(f"Review: {output / 'review/index.html'} (human decision pending)")
    return int(report['status'] != 'validation_passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=tuple(CASES), default='utf8')
    parser.add_argument('--output', type=Path, required=True, help='new directory for logs, run, and portable review')
    args = parser.parse_args()
    try:
        return execute(args.case, args.output)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
