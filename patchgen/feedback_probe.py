"""Bounded live diagnostic-feedback development probe on one rejected case."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from patchgen.generator import api, save
from patchgen.live_analysis import failure_evidence
from patchgen.live_suite import collect
from run_demo import check_output

ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text())


def build_feedback(proposal,case):
    report=read(proposal/'report.json')
    if report['status']=='validation_passed':raise ValueError('feedback probe requires a rejected proposal')
    evidence=failure_evidence(proposal)
    common=evidence.get('compiler_diagnostics',[])
    for name in ('telemetry','pubsub','pubsub-malformed'):
        if name in evidence and evidence[name].get('error'):common=common+[str(evidence[name]['error'])]
    if not common and report.get('error'):common=[report['error'][-4000:]]
    files={}
    for index,file in enumerate(case['affected_files'],1):
        request=proposal/'requests'/f'{index:02d}'
        parsed=request/'parsed-response.json'
        validation=read(request/'edit-validation.json') if (request/'edit-validation.json').is_file() else {}
        diagnostics=([str(validation['error'])] if validation.get('error') else [])+common
        files[file['path']]=dict(previous_response=read(parsed) if parsed.is_file() else {},
                                 validation_diagnostics=diagnostics)
    return dict(source_revision=case['source_revision'],change_id=case['change']['id'],files=files)


def execute(source,output,max_rounds=2):
    if not 1<=max_rounds<=2:raise ValueError('feedback probe is bounded to one or two rounds')
    source=source.resolve();output=check_output(output)
    if source==output or source in output.parents or output in source.parents:
        raise ValueError('feedback output must be outside retained source')
    summary=read(source.parent/'summary.json')
    if summary['status']!='completed' or summary['mode']!='live_model' or summary.get('automatic_repairs')!=0:
        raise ValueError('probe source must be a completed one-shot live suite')
    if source.name not in {row['case'] for row in summary['results']}:raise ValueError('case absent from source suite')
    model=summary['model']
    if model not in ('ministral-3:3b','ministral-3:8b'):raise ValueError('unsupported installed local model')
    previous=source/'run/proposal'
    case=read(previous/'input.json')
    digest=read(previous/'model.json')['tag']['digest']
    if read(previous/'report.json')['status']=='validation_passed':raise ValueError('source proposal already validated')
    initial=collect(source,1,0)
    output.mkdir(parents=True)
    (output/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    report=dict(status='running',protocol='bounded_validation_feedback',case=source.name,model=model,
        model_digest=digest,max_feedback_rounds=max_rounds,initial_model_requests=initial['model_requests'],
        attempts=[],validated_feedback_proposal=False,human_approval_required=True,
        source_summary_sha256=hashlib.sha256((source.parent/'summary.json').read_bytes()).hexdigest(),
        scope='one selected failed development case; not a six-case validation rate, held-out result or model comparison')
    save(output/'summary.json',report)
    for round_number in range(1,max_rounds+1):
        installed=next((tag for tag in api('http://127.0.0.1:11434','/api/tags')['models'] if tag['name']==model),{})
        if installed.get('digest')!=digest:raise ValueError('source model digest changed before feedback attempt')
        target=output/f'attempt-{round_number:02d}';target.mkdir()
        feedback=build_feedback(previous,case)
        save(target/'feedback.json',feedback)
        args=[sys.executable,'-m','patchgen.pipeline','--fixture',str(source/'run/request.json'),
              '--output',str(target/'run'),'--review-output',str(target/'review'),'--generate',
              '--strategy','candidate_feedback_blocks','--feedback',str(target/'feedback.json'),
              '--model',model,'--local-codegen']
        start=time.monotonic()
        with (target/'pipeline.log').open('w') as log:
            code=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
        attempt=collect(target,code,time.monotonic()-start)
        attempt['round']=round_number
        attempt['validated_feedback_proposal']=bool(code==0 and attempt['status']=='validation_passed'
            and attempt.get('mode')=='live_model_feedback' and (target/'review/index.html').is_file())
        report['attempts'].append(attempt)
        save(output/'summary.json',report)
        print(f"Feedback round {round_number}: {attempt['status']}; actual requests={attempt['model_requests']}",flush=True)
        if attempt['validated_feedback_proposal']:
            report['validated_feedback_proposal']=True;break
        if not (target/'run/proposal/report.json').is_file() or not attempt['model_requests']:
            report['stop_reason']='generation_infrastructure';break
        previous=target/'run/proposal'
    report.update(status='completed',feedback_model_requests=sum(a['model_requests'] for a in report['attempts']),
                  total_model_requests_including_initial=initial['model_requests']+sum(a['model_requests'] for a in report['attempts']))
    save(output/'summary.json',report)
    return int(not report['validated_feedback_proposal'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True,help='one case directory in a completed live suite')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--max-rounds',type=int,choices=(1,2),default=2)
    args=parser.parse_args();return execute(args.source,args.output,args.max_rounds)


if __name__=='__main__':raise SystemExit(main())
