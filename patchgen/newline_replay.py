"""Counterfactual offline analysis of recorded block edits; never a live-path repair.

Usage: python -m patchgen.newline_replay CASE_DIR --output NEW_DIR [--unchanged]

The generator's --response consumes a contract_version=1.0 assembled proposal
(outcome, diff, rationale, confidence, assumptions), not per-file block responses.
We resolve those responses with the unmodified host resolver and reproduce the
generator's multi-file assembly before invoking the ordinary pipeline CLI.
Feedback strategies currently reject offline replay; that rejection is evidence,
not permission to substitute another strategy or bypass the validation gate.
"""
import argparse
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from patchgen.anchor_edits import candidates, resolve
from patchgen.generator import ContractError, unified_diff, validate_input, validate_output

ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ('candidate_semantic_blocks', 'candidate_semantic_feedback_blocks')


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_response(value):
    """Copy a response, appending only LF to nonempty before/after lacking LF.

    No whitespace stripping, anchor matching, candidate changes, or semantic fixes.
    Malformed types are preserved for the original resolver to reject.
    """
    result = copy.deepcopy(value)
    changed = []
    if not isinstance(result, dict) or not isinstance(result.get('edits'), list):
        return result, changed
    for index, edit in enumerate(result['edits']):
        if not isinstance(edit, dict):
            continue
        fields = []
        for key in ('before', 'after'):
            text = edit.get(key)
            if isinstance(text, str) and text and not text.endswith('\n'):
                edit[key] = text + '\n'
                fields.append(key)
        if fields:
            changed.append(dict(edit_index=index, appended_lf_to=fields))
    return result, changed


def resolve_record(file, value):
    try:
        return resolve(file['source_context'], value, candidates(file), file['positions']), None
    except (ValueError, KeyError, TypeError) as error:
        return None, dict(path=file['path'], error=str(error))


def assemble(case, records):
    """Match generator.generate's assembly, including host-owned schema diff."""
    assumptions = [f'{r["path"]}: {a}' for r in records for a in r['response']['assumptions']]
    rationale = '\n'.join(f'{r["path"]}: {r["response"]["rationale"]}' for r in records)
    confidence = min(r['response']['confidence'] for r in records)
    clarification = any(r['response']['outcome'] == 'needs_clarification' for r in records)
    diff = '' if clarification else unified_diff(case['change']['schema_path'],
        case['change']['old_schema'], case['change']['new_schema'])
    if not clarification:
        for record, file in zip(records, case['affected_files'], strict=True):
            diff += unified_diff(record['path'], file['source_context'], record['updated_source'])
    return validate_output(dict(contract_version='1.0', outcome='needs_clarification' if clarification
        else 'patch' if diff else 'no_change', diff=diff, rationale=rationale,
        confidence=confidence, assumptions=assumptions))


def verdict(output, process):
    """Retain exact errors and oracle reports; do not equate build with conformance."""
    pipeline_path = output/'run/report.json'
    pipeline = read(pipeline_path) if pipeline_path.exists() else {}
    proposal_path = output/'run/proposal/report.json'
    proposal = read(proposal_path) if proposal_path.exists() else {}
    result = dict(pipeline_exit_code=process.returncode, pipeline_status=pipeline.get('status'),
                  proposal_status=proposal.get('status'))
    oracles = {}
    for name in ('fresh', 'inventory', 'telemetry', 'pubsub', 'pubsub-malformed'):
        path = output/'run/proposal'/name/'report.json'
        if path.exists():
            oracles[name] = read(path)
    result['oracle_verdicts'] = oracles
    error = proposal.get('error') or pipeline.get('error')
    if not error and (output/'run/error.json').exists():
        error = read(output/'run/error.json').get('error')
    if not error and process.returncode:
        error = (output/'pipeline.log').read_text().strip()
    result['error'] = error
    if process.returncode == 0 and pipeline.get('status') == 'validation_passed' and proposal.get('mode') == 'offline_replay':
        result.update(final_status='validation_passed', failing_stage=None)
    else:
        if error and ('feedback requires the live feedback strategy' in error
                      or 'feedback strategy requires explicit live feedback' in error):
            stage = 'offline_replay_strategy_guard'
        elif oracles:
            stage = 'oracle'
        elif (output/'run/proposal/validation.log').exists():
            stage = 'validation'  # Exact failing command/error is retained below and in the log.
        elif proposal:
            stage = 'proposal'
        else:
            stage = 'pipeline'
        result.update(final_status=f'{stage}_failed', failing_stage=stage)
    return result


def replay(case_dir, output, unchanged=False):
    case_dir, output = case_dir.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(mode='offline_replay', counterfactual=True, model_success=False,
        model_requests=0, case_dir=str(case_dir), normalization='unchanged_control' if unchanged else 'append_lf_only',
        original_edit_contract_errors=[], normalized_edit_contract_errors=[], changed_edits=[],
        final_status='replay_unavailable', human_approval_required=True,
        tool_sha256=sha256(Path(__file__)))
    try:
        run = case_dir/'run'
        fixture = run/'request.json'
        case = validate_input(read(run/'input.json'))
        original_report = read(run/'proposal/report.json')
        strategy = original_report['strategy']
        if strategy not in STRATEGIES:
            raise ContractError(f'unsupported recorded strategy: {strategy}')
        report.update(strategy=strategy, original_status=original_report['status'],
                      original_error=original_report.get('error'), fixture_sha256=sha256(fixture),
                      recorded_input_sha256=sha256(run/'input.json'), recorded_files=[])
        request = read(fixture)
        if (request['source_revision'] != case['source_revision'] or request['change']['id'] != case['change']['id']
                or any(request['change'][key] != case['change'][key] for key in ('old_schema', 'new_schema', 'schema_path'))
                or request['intended_behavior'] != case['intended_behavior']):
            raise ContractError('recorded request and prepared input disagree')
        records, missing = [], []
        for index, file in enumerate(case['affected_files'], 1):
            directory = run/'proposal/requests'/f'{index:02d}'
            parsed = directory/'parsed-response.json'
            if not parsed.is_file():
                missing.append(str(parsed))
                continue
            # Use prompt identity as well as positional numbering to prevent misassignment.
            prompt = read(directory/'prompt.json')
            payload = json.loads(prompt['messages'][1]['content'])
            if (payload['file']['path'] != file['path'] or payload['file']['source_context'] != file['source_context']):
                raise ContractError(f'recorded prompt/input mismatch: {file["path"]}')
            if read(directory/'token-inventory.json') != candidates(file):
                raise ContractError(f'recorded candidate inventory mismatch: {file["path"]}')
            original = read(parsed)
            normalized, changes = (copy.deepcopy(original), []) if unchanged else normalize_response(original)
            target = output/'responses'/f'{index:02d}'
            save(target/'original.json', original)
            save(target/'normalized.json', normalized)
            report['recorded_files'].append(dict(path=file['path'], parsed_response_sha256=sha256(parsed)))
            report['changed_edits'].extend(dict(path=file['path'], **change) for change in changes)
            _, original_error = resolve_record(file, original)
            updated, normalized_error = resolve_record(file, normalized)
            if original_error:
                report['original_edit_contract_errors'].append(original_error)
            if normalized_error:
                report['normalized_edit_contract_errors'].append(normalized_error)
            records.append(dict(path=file['path'], response=normalized, updated_source=updated))
        if missing:
            raise ContractError('missing recorded parsed responses: ' + ', '.join(missing))
        if report['normalized_edit_contract_errors']:
            report.update(final_status='edit_contract_failed', failing_stage='edit_contract')
        else:
            response = output/'response.json'
            save(response, assemble(case, records))
            command = [sys.executable, '-m', 'patchgen.pipeline', '--fixture', str(fixture),
                       '--output', str(output/'run'), '--strategy', strategy,
                       '--response', str(response), '--local-codegen']
            # No --generate, --feedback, or cloud backend: no credentials or model calls.
            report['command'] = command
            save(output/'report.json', report)
            with (output/'pipeline.log').open('w') as log:
                process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            report.update(verdict(output, process))
            prepared = output/'run/input.json'
            if prepared.exists():
                report['prepared_input_matches_recorded'] = read(prepared) == case
                if not report['prepared_input_matches_recorded']:
                    report.update(final_status='prepared_input_mismatch', failing_stage='reproducibility')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
    save(output/'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case_dir', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='new evidence directory')
    parser.add_argument('--unchanged', action='store_true', help='control: preserve all recorded response content')
    args = parser.parse_args()
    # A shared nonblocking lock prevents concurrent invocations of this replay tool.
    lock = ROOT/'patchgen/evidence/newline-replay/.pipeline.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('another newline replay is running; pipelines must be sequential')
        report = replay(args.case_dir, args.output, args.unchanged)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report['final_status'] != 'validation_passed')


if __name__ == '__main__':
    raise SystemExit(main())
