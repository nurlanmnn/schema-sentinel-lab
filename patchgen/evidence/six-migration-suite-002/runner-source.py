"""Run six distinct authored migrations sequentially; preserve every outcome."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import run_demo

ROOT = Path(__file__).resolve().parent
# Transport variants, negative controls and reference replays are not extra cases.
CASES = ('pubsub-rename', 'pubsub-removal', 'pubsub-utf8',
         'telemetry-rename', 'telemetry-precision', 'telemetry-units')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    result = []
    for name in CASES:
        profile, strategy = run_demo.CASES[name]
        fixture_path = ROOT / 'patchgen/fixtures' / profile / 'runtime-input.json'
        truth_path = ROOT / 'patchgen/reference' / profile / 'expected.json'
        fixture, truth = read(fixture_path), read(truth_path)
        if truth.get('source_revision', fixture['source_revision']) != fixture['source_revision'] or truth.get('change_id', fixture['change']['id']) != fixture['change']['id']:
            raise RuntimeError(f'{name}: ground truth identity mismatch')
        count = sum(len(site.get('lines', site.get('positions', []))) for site in truth['runtime_sites'])
        if not count:
            raise RuntimeError(f'{name}: missing ground truth sites')
        result.append(dict(case=name, profile=profile, strategy=strategy,
                           source_revision=fixture['source_revision'],
                           structural_category=truth['category'], expected_sites=count,
                           fixture_sha256=digest(fixture_path), ground_truth_sha256=digest(truth_path)))
    return result


def collect(entry, target, exit_code, elapsed):
    row = dict(entry, status='failed', exit_code=exit_code, elapsed_seconds=elapsed,
               matched_sites=0, extra_sites=0, measurement_available=False,
               classification_correct=False, review='human_decision_pending',
               evidence=str(target.relative_to(target.parent)))
    try:
        demo, pipeline = read(target / 'demo-report.json'), read(target / 'run/report.json')
        metrics = pipeline.get('measurement')
        if not isinstance(metrics, dict) or metrics.get('expected_sites') != entry['expected_sites']:
            raise ValueError('missing or incompatible impact measurement')
        matched = metrics['matched_sites']
        if type(matched) is not int or not 0 <= matched <= entry['expected_sites']:
            raise ValueError('invalid matched-site count')
        row.update(measurement_available=True, matched_sites=matched,
                   extra_sites=len(metrics['extra']), classification_correct=metrics['classification_correct'] is True)
        proposal = pipeline.get('proposal_report', {})
        row['pipeline_seconds'] = proposal.get('workflow_elapsed_seconds')
        row['runtime_validation'] = proposal.get('telemetry_validation', proposal.get('pubsub_validation'))
        row['strategy_observed'] = proposal.get('strategy')
        if (exit_code == 0 and demo['status'] == pipeline['status'] == 'validation_passed'
                and proposal.get('mode') == 'deterministic_proposal'
                and proposal.get('strategy') == entry['strategy']
                and pipeline.get('source_revision') == entry['source_revision']
                and isinstance(row['runtime_validation'], dict)
                and row['runtime_validation'].get('status') == 'passed'
                and (target / 'review/index.html').is_file()):
            row['status'] = 'validation_passed'
        else:
            row['error'] = 'demo, pipeline, runtime evidence or review did not pass; inspect retained logs'
        row['report_sha256'] = {str(p.relative_to(target)): digest(p) for p in
                               (target / 'demo-report.json', target / 'run/report.json')}
    except (OSError, ValueError, KeyError, TypeError) as error:
        row['error'] = str(error)
    return row


def summarize(rows):
    expected = sum(r['expected_sites'] for r in rows)
    return dict(distinct_migration_cases=len(rows), validation_passed=sum(r['status'] == 'validation_passed' for r in rows),
                validation_rate=sum(r['status'] == 'validation_passed' for r in rows) / len(rows),
                classification_correct=sum(r['classification_correct'] for r in rows),
                classification_accuracy=sum(r['classification_correct'] for r in rows) / len(rows),
                impact_measurements_available=sum(r['measurement_available'] for r in rows),
                expected_sites=expected, matched_sites=sum(r['matched_sites'] for r in rows),
                impact_recall=sum(r['matched_sites'] for r in rows) / expected,
                extra_sites=sum(r['extra_sites'] for r in rows))



def render_summary(report, entries):
    """Readable evidence index; pending cases stay visible during a partial run."""
    rows = {row['case']: row for row in report['results']}
    lines = ['# Six-migration evaluation', '',
             'Status: ' + report['status'] + '. Deterministic authored cases; human decisions pending.', '',
             '| Migration | Validation | Structural category correct | Candidate lines | Extras | Evidence |',
             '| --- | --- | --- | --- | --- | --- |']
    for entry in entries:
        name = entry['case']
        row = rows.get(name)
        if row is None:
            lines.append(f"| {name} | pending | unmeasured | unmeasured/{entry['expected_sites']} | unmeasured | pending |")
            continue
        category = str(row['classification_correct']).lower() if row['measurement_available'] else 'unmeasured'
        matched = str(row['matched_sites']) if row['measurement_available'] else 'unmeasured'
        extras = str(row['extra_sites']) if row['measurement_available'] else 'unmeasured'
        evidence = f"[log]({name}.log)"
        if row['status'] == 'validation_passed':
            evidence += f", [review]({name}/review/index.html)"
        lines.append(f"| {name} | {row['status']} | {category} | {matched}/{entry['expected_sites']} | {extras} | {evidence} |")
    lines += ['', 'All six cases remain in completed-suite denominators. Missing measurements count as zero matched sites and incorrect classification.',
              '', 'Timings include bootstrap and prepared-fixture work. Live model performance and human review time are unmeasured.',
              'This is six small authored migrations, not the twenty-case MVP benchmark. Structural classification does not infer units.',
              '', '[Machine-readable summary](summary.json) · [Pinned manifest](manifest.json)', '']
    return '\n'.join(lines)


def execute(output, local_codegen=False):
    output = run_demo.check_output(output)
    entries = manifest()
    output.mkdir(parents=True)
    (output / 'runner-source.py').write_bytes(Path(__file__).read_bytes())
    (output / 'manifest.json').write_text(json.dumps(entries, indent=2) + '\n')
    report = dict(status='running', mode='deterministic_authored_suite', model_requests=0,
                  human_approval_required=True, human_review_seconds=None, live_model_validation_rate=None,
                  timing_scope='sequential prepared demos including bootstrap; not operational propagation time',
                  scope='six small authored migrations; not the twenty-case MVP benchmark; structural classification only',
                  missing_measurement_policy='zero matched sites and incorrect classification; all six remain in denominators',
                  implementation_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  implementation_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)),
                  runner_sha256=digest(Path(__file__)), results=[])
    def save():
        (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
        (output / 'summary.md').write_text(render_summary(report, entries))
    save()
    started = time.monotonic()
    for entry in entries:
        target = output / entry['case']
        command = [sys.executable, str(ROOT / 'run_demo.py'), '--case', entry['case'], '--output', str(target)]
        if local_codegen:
            command.append('--local-codegen')
        before = time.monotonic()
        with (output / (entry['case'] + '.log')).open('w') as log:
            try:
                code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
            except OSError as error:
                log.write(str(error) + '\n')
                code = 1
        report['results'].append(collect(entry, target, code, time.monotonic() - before))
        save()
        print(entry['case'] + ': ' + report['results'][-1]['status'], flush=True)
    report.update(status='completed', metrics=summarize(report['results']), elapsed_seconds=time.monotonic() - started)
    save()
    print(json.dumps(report['metrics'], indent=2))
    return int(report['metrics']['validation_passed'] != len(CASES))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new evidence directory')
    parser.add_argument('--local-codegen', action='store_true')
    args = parser.parse_args()
    try:
        return execute(args.output, args.local_codegen)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
