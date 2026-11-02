"""Summarize completed live-suite evidence without changing retained runs."""
import argparse
import hashlib
import json
from pathlib import Path
from patchgen.live_suite import CASES


def read(path):
    return json.loads(path.read_text())


def analyze(source,output):
    source,output=source.resolve(),output.resolve()
    if output.exists() or output==source or output in source.parents or source in output.parents:
        raise ValueError('analysis output must be new and outside retained suite')
    summary=read(source/'summary.json')
    if summary['status']!='completed' or summary['mode']!='live_model' or {r['case'] for r in summary['results']}!=set(CASES):
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
                         generation_seconds=record['generation_seconds'],workflow_seconds=record['workflow_seconds'],error=record.get('error')))
    model_paths=[source/r['case']/'run/proposal/model.json' for r in summary['results']]
    models=[read(path) for path in model_paths if path.is_file()]
    digests={m['tag']['digest'] for m in models}
    if len(digests)!=1:
        raise ValueError('suite did not retain one consistent model digest')
    output.mkdir(parents=True)
    result=dict(mode='live_model',model=summary['model'],model_digest=next(iter(digests)),options=summary['options'],
                prompt_version=summary['prompt_version'],source_summary_sha256=hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),
                validated_model_patches=sum(r['validated'] for r in rows),planned_cases=len(CASES),
                validation_rate=sum(r['validated'] for r in rows)/len(CASES),rows=rows,
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
    (output/'analysis.md').write_text('\n'.join(lines))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=analyze(args.source,args.output)
    print(json.dumps(result,indent=2))


if __name__=='__main__':raise SystemExit(main())
