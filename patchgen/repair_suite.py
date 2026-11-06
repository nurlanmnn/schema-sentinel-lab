"""Bounded validation-feedback repair rounds on a completed locked suite (decision 0042)."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from patchgen.generator import save
from patchgen.nvidia_client import options_for
from patchgen.live_suite import LOCKED_CONFIG, LOCKED_DECISION, collect, prompt_fingerprints, require_locked_prompts
from run_demo import check_output

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = 'candidate_semantic_feedback_blocks'
ORACLES = ('telemetry', 'pubsub', 'pubsub-malformed', 'inventory')
COMPILER = re.compile(r'error (?:TS\d+|CS\d+)|SyntaxError:|IndentationError:')
LINE_LIMIT, LINES_PER_FILE = 500, 20


def read(path): return json.loads(path.read_text())


RUNTIMES = ('python', 'typescript', 'csharp')
PYTHON_SYNTAX = re.compile(r'^(?P<message>[^()\n]+) \((?P<file>[\w.-]+\.py), line (?P<line>\d+)\)$')


def compiler_lines(log, paths):
    """Keep compiler errors located in model-edited files only; evaluator-owned tests stay hidden."""
    kept, withheld = [], 0
    for line in dict.fromkeys(l for l in log.splitlines() if COMPILER.search(l)):
        # Drop absolute workspace prefixes and trailing project annotations.
        line = re.sub(r'^.*?/workspace/', '', re.sub(r'\s*\[[^\]]*\.csproj\]$', '', line)).strip()
        # The diagnostic's own location must be an edited file, not a path mentioned in its message.
        if any(re.match(re.escape(path) + r'[(:]', line) for path in paths):kept.append(line[:LINE_LIMIT])
        else:withheld += 1
    return kept, withheld


def python_syntax(report, paths):
    """ast.parse errors are recorded as `message (main.py, line N)` in the generator report."""
    match = PYTHON_SYNTAX.match(str(report.get('error') or ''))
    owners = [path for path in paths if path.endswith('.py') and Path(path).name == (match and match['file'])]
    return [f"SyntaxError: {match['message'][:200]} ({owners[0]}, line {match['line']})"] if len(owners) == 1 else []


def oracle_verdict(name, error):
    """Fixed wording: free-form oracle errors can embed expected values, so only a case index or runtime is kept."""
    case = re.search(r'\bat case (\d+)$', error)
    runtime = next((r for r in RUNTIMES if error.startswith(r + ':')), None)
    return f'{name} runtime check failed' + (f' at authored case {case[1]}' if case else '') + (f' in the {runtime} service' if runtime else '')


def build_feedback(proposal, case):
    """Diagnostics only: compiler errors in edited files, edit-contract errors and oracle verdicts."""
    report = read(proposal/'report.json')
    if report['status'] == 'validation_passed':raise ValueError('repair requires a rejected proposal')
    paths = [file['path'] for file in case['affected_files']]
    common, withheld = [], 0
    if (proposal/'validation.log').is_file():
        common, withheld = compiler_lines((proposal/'validation.log').read_text(), paths)
    common += python_syntax(report, paths)
    for name in ORACLES:
        path = proposal/name/'report.json'
        if path.is_file() and read(path).get('status') not in (None, 'passed', 'expected_rejection_observed'):
            common.append(oracle_verdict(name, str(read(path).get('error') or '')))
    files = {}
    for index, path in enumerate(paths, 1):
        request = proposal/'requests'/f'{index:02d}'
        validation = read(request/'edit-validation.json') if (request/'edit-validation.json').is_file() else {}
        own = ['edit contract rejected: ' + str(validation['error'])[:LINE_LIMIT]] if validation.get('error') else []
        fallback = ('edits for this file were accepted; another file or check rejected the proposal'
                    if validation.get('status') == 'passed' else 'validation rejected without file-specific diagnostics')
        diagnostics = (own + common)[:LINES_PER_FILE] or [fallback]
        files[path] = dict(previous_response=read(request/'parsed-response.json') if (request/'parsed-response.json').is_file() else {},
                           validation_diagnostics=diagnostics)
    return (dict(source_revision=case['source_revision'], change_id=case['change']['id'], files=files),
            dict(withheld_compiler_lines=withheld))


def failure_stage(target, result):
    """Separate response format, compilation and behavior failures; acceptance is decided by the caller."""
    proposal = target/'run/proposal'
    if result['status'] == 'provider_unavailable':return 'provider_unavailable'
    if not result['model_requests']:return 'no_model_request'
    # Passing checks without exit code 0, live mode and a review bundle is not an accepted patch.
    if result['status'] == 'validation_passed':return 'incomplete_acceptance'
    if any(r.get('edit_validation', {}).get('status') == 'failed' for r in result['requests']):
        return 'response_or_edit_contract'
    if (proposal/'validation.log').is_file() and COMPILER.search((proposal/'validation.log').read_text()):
        return 'compilation'
    if any((proposal/name/'report.json').is_file() and read(proposal/name/'report.json').get('status')
           not in ('passed', 'expected_rejection_observed') for name in ORACLES):
        return 'runtime_semantics'
    return result['status'] if result['status'] in ('needs_clarification', 'no_change') else 'other_validation'


def require_locked_source(source):
    summary = read(source/'summary.json')
    if (summary.get('status') != 'completed' or summary.get('mode') != 'live_model' or summary.get('automatic_repairs') != 0
            or summary.get('locked_configuration') != LOCKED_DECISION
            or {key: summary.get(key) for key in LOCKED_CONFIG} != LOCKED_CONFIG
            or summary.get('prompt_fingerprints') != prompt_fingerprints()
            or summary.get('options') != options_for(LOCKED_CONFIG['model'])):
        raise ValueError('repair source must be a completed one-shot locked suite with unchanged prompts')
    # Retained requests must show the locked model and sampling actually sent.
    for request in source.glob('*/run/proposal/requests/*/request.json'):
        sent = read(request)
        if sent.get('model') != LOCKED_CONFIG['model'] or {k: sent.get(k) for k in options_for(LOCKED_CONFIG['model'])} != options_for(LOCKED_CONFIG['model']):
            raise ValueError('retained request does not match the locked model and sampling: ' + str(request.relative_to(source)))
    return summary


def execute(source, output, max_rounds=2):
    if not 1 <= max_rounds <= 2:raise ValueError('repair is bounded to one or two rounds')
    source = source.resolve(); output = check_output(output)
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('repair output must be outside the retained source suite')
    require_locked_prompts()
    summary = require_locked_source(source)
    if summary.get('held_out_registry'):
        # The seal must still hold, and be the very registry the one-shot run used.
        from patchgen import held_out
        registry = ROOT/summary['held_out_registry']
        held_out.verify(registry)
        if held_out.registry_sha256(registry) != summary.get('held_out_registry_sha256'):
            raise ValueError('held-out registry differs from the one used by the source run')
        # One repair per attempt, on evidence byte-identical to what the ledger recorded at completion.
        held_out.begin_repair(registry, source, output)
        sealed_fixtures = {e['case']: ROOT/'patchgen/fixtures'/e['profile']/'runtime-input.json' for e in read(source/'manifest.json')}
    output.mkdir(parents=True)
    (output/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    report = dict(status='running', protocol='bounded_validation_feedback_repair', locked_configuration=LOCKED_DECISION,
        **LOCKED_CONFIG, repair_strategy=STRATEGY, max_rounds=max_rounds, human_approval_required=True,
        source_summary_sha256=hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),
        prompt_fingerprints=prompt_fingerprints(), cases=[],
        held_out_registry=summary.get('held_out_registry'), held_out_registry_sha256=summary.get('held_out_registry_sha256'),
        # Repair learns from each case's own oracle verdicts, so held-out repair is never the headline score.
        result_kind='held_out_with_validation_feedback' if summary.get('held_out_registry') else 'development_with_validation_feedback',
        scope='repair rounds after a one-shot locked suite; repaired passes are never first-pass successes')
    save(output/'summary.json', report)
    stopped = False
    for row in summary['results']:
        name = row['case']
        first = 'validated' if row['generated_patch_validated'] else failure_stage(source/name, row)
        record = dict(case=name, split=(summary.get('case_split') or {}).get(name, 'development'), first_pass_stage=first, attempts=[], validated_round=0 if first == 'validated' else None)
        report['cases'].append(record)
        if first in ('validated', 'provider_unavailable', 'no_model_request') or stopped:
            record['skipped'] = 'not_repairable' if not stopped else 'suite_stopped'
            continue
        previous = source/name/'run/proposal'
        for round_number in range(1, max_rounds + 1):
            target = output/name/f'round-{round_number}'; target.mkdir(parents=True)
            feedback, meta = build_feedback(previous, read(previous/'input.json'))
            save(target/'feedback.json', feedback)
            # Held-out repair reads the sealed fixture, never the retained copy.
            fixture = sealed_fixtures[name] if summary.get('held_out_registry') else source/name/'run/request.json'
            command = [sys.executable, '-m', 'patchgen.pipeline', '--fixture', str(fixture),
                       '--output', str(target/'run'), '--review-output', str(target/'review'), '--generate',
                       '--strategy', STRATEGY, '--feedback', str(target/'feedback.json'), '--model', LOCKED_CONFIG['model'],
                       '--backend', LOCKED_CONFIG['backend'], '--local-codegen']
            start = time.monotonic()
            with (target/'pipeline.log').open('w') as log:
                try:code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
                except OSError as error:log.write(str(error)); code = 1
            attempt = dict(round=round_number, **meta, **collect(target, code, time.monotonic() - start))
            attempt['validated'] = bool(code == 0 and attempt['status'] == 'validation_passed' and attempt['model_requests']
                                        and attempt.get('mode') == 'live_model_feedback' and (target/'review/index.html').is_file())
            attempt['stage'] = 'validated' if attempt['validated'] else failure_stage(target, attempt)
            record['attempts'].append(attempt); save(output/'summary.json', report)
            print(f"{name} round {round_number}: {attempt['stage']}; actual requests={attempt['model_requests']}", flush=True)
            if attempt['stage'] == 'provider_unavailable':stopped = True; break
            if attempt['validated']:record['validated_round'] = round_number; break
            if not (target/'run/proposal/report.json').is_file():break
            previous = target/'run/proposal'
    total = len(report['cases'])
    within = lambda limit: sum(c['validated_round'] is not None and c['validated_round'] <= limit for c in report['cases'])
    report.update(status='provider_unavailable' if stopped else 'completed', planned_cases=total,
        first_pass_validated=within(0), validated_within_rounds={str(n): within(n) for n in range(1, max_rounds + 1)},
        first_pass_stages={c['case']: c['first_pass_stage'] for c in report['cases']},
        repair_model_requests=sum(a['model_requests'] for c in report['cases'] for a in c['attempts']))
    if summary.get('cohorts'):
        # Registry cohorts keep withdrawn and unattempted cases in each denominator and variants apart.
        rounds = {c['case']: c['validated_round'] for c in report['cases']}
        upto = lambda names, limit: f"{sum(rounds.get(n) is not None and rounds[n] <= limit for n in names)}/{len(names)}"
        report['validated_by_cohort'] = {cohort: {str(limit): upto(names, limit) for limit in range(max_rounds + 1)}
                                         for cohort, names in summary['cohorts'].items()}
        total = len(summary['cohorts']['headline'])
        save(output/'summary.json', report)
        return int(sum(rounds.get(n) is not None for n in summary['cohorts']['headline']) != total)
    save(output/'summary.json', report)
    return int(within(max_rounds) != total)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='a completed `live_suite --locked` output directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-rounds', type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    try:
        return execute(args.source, args.output, args.max_rounds)
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':raise SystemExit(main())
