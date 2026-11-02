"""Summarize completed live-suite evidence without changing retained runs."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from patchgen.live_suite import CASES


def read(path):
    return json.loads(path.read_text())


def request_details(root, requests):
    """Read only top-level request artifacts, never archived source worktrees."""
    details=[]
    for request in requests:
        directory=root/'requests'/request['request']
        validation=request.get('edit_validation',{})
        counts=request.get('serving_counts',{})
        row=dict(request=request['request'],path=validation.get('path'),
                 contract_status=validation.get('status'),error=validation.get('error'))
        for key in ('load_duration','prompt_eval_duration','eval_duration','total_duration'):
            value=counts.get(key)
            row[key.replace('_duration','_seconds')]=value/1e9 if isinstance(value,(int,float)) else None
        row['input_tokens']=counts.get('prompt_eval_count')
        row['output_tokens']=counts.get('eval_count')
        row['output_tokens_per_second']=(row['output_tokens']/row['eval_seconds']
            if row['output_tokens'] is not None and row['eval_seconds'] else None)
        # Confidence is retained for inspection, never used as a validation gate.
        parsed=directory/'parsed-response.json'
        if parsed.is_file():
            response=read(parsed)
            row.update(outcome=response.get('outcome'),confidence=response.get('confidence'),
                       rationale=response.get('rationale'))
        details.append(row)
    return details


def failure_evidence(root):
    result={}
    log=root/'validation.log'
    if log.is_file():
        # Preserve concrete compiler messages without copying dependency installation logs.
        result['compiler_diagnostics']=list(dict.fromkeys(line for line in log.read_text().splitlines()
            if re.search(r'error (?:TS\d+|CS\d+)|SyntaxError:|IndentationError:',line)))
    for name in ('telemetry','pubsub','pubsub-malformed'):
        path=root/name/'report.json'
        if path.is_file():result[name]=read(path)
    return result


def analyze(source,output):
    source,output=source.resolve(),output.resolve()
    if output.exists() or output==source or output in source.parents or source in output.parents:
        raise ValueError('analysis output must be new and outside retained suite')
    summary=read(source/'summary.json')
    if (summary['status']!='completed' or summary['mode']!='live_model'
            or len(summary['results'])!=len(CASES) or {r['case'] for r in summary['results']}!=set(CASES)):
        raise ValueError('analysis requires a completed six-case live suite')
    rows=[]
    for record in summary['results']:
        name=record['case'];root=source/name/'run/proposal'
        requests=record['requests']
        if record['generated_patch_validated']:
            reason='validated_proposal'
        elif not record['model_requests']:
            reason='generation_infrastructure'
        elif any(r.get('edit_validation',{}).get('status')=='failed' for r in requests):
            reason='file_contract_or_generation_rejected'
        elif record['status'] in ('needs_clarification','no_change'):
            reason=record['status']
        elif re.search(r'\([^,\n]*\.py, line \d+\)',record.get('error') or ''):
            # ast.parse failures are retained as SyntaxError strings before build logs.
            reason='python_syntax'
        elif (root/'telemetry/report.json').is_file() and read(root/'telemetry/report.json').get('status')!='passed':
            reason='independent_telemetry_semantics'
        elif (root/'pubsub/report.json').is_file() and read(root/'pubsub/report.json').get('status')!='passed':
            reason='independent_pubsub_semantics'
        elif (root/'pubsub-malformed/report.json').is_file() and read(root/'pubsub-malformed/report.json').get('status')!='expected_rejection_observed':
            reason='negative_control'
        elif (root/'validation.log').is_file() and any(marker in (root/'validation.log').read_text() for marker in ('error TS','error CS','Build FAILED')):
            reason='compilation'
        else:
            reason='workflow_validation_rejected'
        rows.append(dict(case=name,outcome=reason,validated=record['generated_patch_validated'],model_requests=record['model_requests'],
                         generation_seconds=record['generation_seconds'],workflow_seconds=record['workflow_seconds'],error=record.get('error'),
                         requests=request_details(root,requests),failure_evidence=failure_evidence(root)))
        if reason=='python_syntax':rows[-1]['failure_evidence']['python_syntax']=record['error']
    model_paths=[source/r['case']/'run/proposal/model.json' for r in summary['results']]
    if not all(path.is_file() for path in model_paths):
        raise ValueError('suite is missing per-case model identity evidence')
    models=[read(path) for path in model_paths]
    digests={m['tag']['digest'] for m in models}
    if len(digests)!=1:
        raise ValueError('suite did not retain one consistent model digest')
    output.mkdir(parents=True)
    result=dict(mode='live_model',model=summary['model'],model_digest=next(iter(digests)),options=summary['options'],
                prompt_version=summary['prompt_version'],source_summary_sha256=hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),
                validated_model_patches=sum(r['validated'] for r in rows),planned_cases=len(CASES),
                validation_rate=sum(r['validated'] for r in rows)/len(CASES),rows=rows,
                contract_results=dict(passed=sum(request['contract_status']=='passed' for row in rows for request in row['requests']),
                                      failed=sum(request['contract_status']=='failed' for row in rows for request in row['requests']),
                                      unknown=sum(request['contract_status'] not in ('passed','failed') for row in rows for request in row['requests'])),
                timing_scope='Ollama load/prompt/eval counters per request; load duration alone does not prove cold versus warm cache state',
                scope='six small authored cases; one trial per model, no repairs; not general reliability or human acceptance')
    (output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Live model patch evaluation','',f"Model: {result['model']} (`{result['model_digest']}`).",
           f"Validated proposals: {result['validated_model_patches']}/{len(CASES)}. Human approval pending.",'',
           '| Migration | Outcome | Model requests | Generation seconds | Pipeline seconds |',
           '| --- | --- | ---: | ---: | ---: |']
    for row in rows:
        lines.append(f"| {row['case']} | {row['outcome']} | {row['model_requests']} | {row['generation_seconds']:.2f} | {row['workflow_seconds']:.2f} |")
    lines+=['','Generation includes local loading/inference wall time; pipeline includes independent analysis and validation.',
            'Contract/generation rejections do not establish compilation or runtime behavior. Deterministic and reference replays are excluded.',
            'This small single-trial suite is not a broad model comparison, twenty-case benchmark or human review baseline.','']
    lines+=['## Request timing','',
            'These are serving counters, not a controlled cold/warm comparison. Missing counters remain unknown.','',
            '| Migration/request | File | Contract | Load s | Prompt s | Decode s | Output tokens |',
            '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    def display(value):return 'unknown' if value is None else f'{value:.2f}' if isinstance(value,float) else str(value)
    for row in rows:
        for request in row['requests']:
            lines.append('| '+' | '.join(display(value) for value in
                (row['case']+'/'+request['request'],request['path'],request['contract_status'],
                 request['load_seconds'],request['prompt_eval_seconds'],request['eval_seconds'],request['output_tokens']))+' |')
    for row in rows:
        diagnostics=row['failure_evidence'].get('compiler_diagnostics',[])
        if row['failure_evidence'].get('python_syntax'):diagnostics=diagnostics+[row['failure_evidence']['python_syntax']]
        errors=[request for request in row['requests'] if request['error']]
        if diagnostics or errors:
            lines+=['',f"## {row['case']} rejection evidence",'']
            lines.extend('- '+message for message in diagnostics)
            lines.extend('- Request '+request['request']+': '+str(request['error']) for request in errors)
    lines.append('')
    (output/'analysis.md').write_text('\n'.join(lines))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=analyze(args.source,args.output)
    print(json.dumps(result,indent=2))


if __name__=='__main__':raise SystemExit(main())
