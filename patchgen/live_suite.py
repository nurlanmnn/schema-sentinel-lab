"""Measure actual local LLM proposals on six fixed independently validated migrations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from patchgen.generator import OPTIONS, STRATEGY_VERSIONS
from run_benchmark import manifest
from run_demo import check_output

ROOT = Path(__file__).resolve().parents[1]
CASES = ('pubsub-rename','pubsub-removal','pubsub-utf8','telemetry-rename','telemetry-precision','telemetry-units')


def collect(target, exit_code, elapsed):
    result = dict(exit_code=exit_code,status='failed',workflow_seconds=elapsed,model_requests=0,
                  generation_seconds=0,generated_patch_validated=False,human_approval_required=True)
    report_path = target/'run/report.json'
    if report_path.is_file():
        pipeline = json.loads(report_path.read_text())
        proposal = pipeline.get('proposal_report',{})
        result.update(status=pipeline['status'],measurement=pipeline.get('measurement'),
                      error=proposal.get('error',pipeline.get('error')),mode=proposal.get('mode'))
        result['generated_patch_validated'] = bool(exit_code==0 and pipeline['status']=='validation_passed'
            and proposal.get('mode')=='live_model' and (target/'review/index.html').is_file())
        result['runtime_validation'] = proposal.get('telemetry_validation',proposal.get('pubsub_validation'))
    requests=[]
    for directory in sorted((target/'run/proposal/requests').glob('*')):
        item = {'request':directory.name}
        for filename,key in [('edit-validation.json','edit_validation'),('request-measurement.json','measurement')]:
            if (directory/filename).is_file():item[key]=json.loads((directory/filename).read_text())
        if (directory/'request.json').is_file():
            result['model_requests']+=1
            item['request_sha256']=hashlib.sha256((directory/'request.json').read_bytes()).hexdigest()
        result['generation_seconds']+=item.get('measurement',{}).get('elapsed_seconds',0)
        if (directory/'raw-response.json').is_file():
            raw=json.loads((directory/'raw-response.json').read_text())
            item['serving_counts']={key:raw.get(key) for key in ('done','done_reason','prompt_eval_count','eval_count','total_duration','load_duration','prompt_eval_duration','eval_duration')}
        # Full memory samples remain in their original request-measurement artifacts.
        if 'measurement' in item:item['measurement']={key:value for key,value in item['measurement'].items() if key!='memory_samples'}
        requests.append(item)
    result['requests']=requests
    return result


def execute(output,model,strategy='candidate_edits'):
    if strategy not in ('candidate_edits','candidate_blocks'):
        raise ValueError('live suite requires a supported live model strategy')
    output=check_output(output);output.mkdir(parents=True)
    entries=[e for e in manifest() if e['case'] in CASES]
    (output/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    (output/'manifest.json').write_text(json.dumps(entries,indent=2)+'\n')
    report=dict(status='running',mode='live_model',model=model,strategy=strategy,
                prompt_version=STRATEGY_VERSIONS[strategy],options=OPTIONS,
                planned_cases=len(entries),automatic_repairs=0,human_approval_required=True,
                implementation_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                implementation_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
                scope='six authored migrations with actual model-generated runtime edits; not broad model quality or twenty-case MVP',
                timing_scope='per-request wall time includes local model load; prepared pipeline wall time separate; not propagation/human baseline',results=[])
    def save():(output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for entry in entries:
        target=output/entry['case'];target.mkdir()
        command=[sys.executable,'-m','patchgen.pipeline','--fixture',str(ROOT/'patchgen/fixtures'/entry['profile']/'runtime-input.json'),
                 '--output',str(target/'run'),'--generate','--strategy',strategy,'--model',model,'--local-codegen',
                 '--review-output',str(target/'review')]
        start=time.monotonic()
        with (target/'pipeline.log').open('w') as log:
            try:code=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
            except OSError as error:log.write(str(error));code=1
        result=dict(case=entry['case'],**collect(target,code,time.monotonic()-start))
        report['results'].append(result);save()
        print(result['case']+': '+result['status']+'; actual model requests='+str(result['model_requests']),flush=True)
    passed=sum(r['generated_patch_validated'] for r in report['results'])
    report.update(status='completed',validated_model_patches=passed,model_patch_validation_rate=passed/len(entries),
                  model_requests=sum(r['model_requests'] for r in report['results']),
                  generation_seconds=sum(r['generation_seconds'] for r in report['results']))
    save()
    return int(passed!=len(entries))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model',choices=('ministral-3:3b','ministral-3:8b'),default='ministral-3:8b')
    parser.add_argument('--strategy',choices=('candidate_edits','candidate_blocks'),default='candidate_edits')
    args=parser.parse_args()
    return execute(args.output,args.model,args.strategy)


if __name__=='__main__':raise SystemExit(main())
