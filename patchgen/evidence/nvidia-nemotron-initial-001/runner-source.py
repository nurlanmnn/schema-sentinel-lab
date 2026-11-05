"""Measure actual local LLM proposals on migrations supported by the live route."""
from patchgen.nvidia_client import MODEL as NVIDIA_MODEL
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from patchgen.generator import LOCAL_MODELS, OPENROUTER_MODEL, OPTIONS, STRATEGY_VERSIONS
from run_benchmark import manifest
from run_demo import check_output

ROOT = Path(__file__).resolve().parents[1]
CASES = ('pubsub-rename','pubsub-removal','pubsub-utf8','telemetry-rename','telemetry-precision','telemetry-units')
ADDITIONAL_CASES = ('inventory-width', 'telemetry-quantized')
SCHEMA_ONLY_CASES = ('inventory-zigzag', 'telemetry-tag-move', 'inventory-packed-bins')


def benchmark_plan(entries):
    return {entry['case']: (
        'eligible' if entry['case'] in CASES + ADDITIONAL_CASES else
        'schema_only' if entry['case'] in SCHEMA_ONLY_CASES else
        'requires_pinned_policy'
    ) for entry in entries}


def collect(target, exit_code, elapsed):
    result = dict(exit_code=exit_code,status='failed',workflow_seconds=elapsed,model_requests=0,
                  generation_seconds=0,generated_patch_validated=False,human_approval_required=True)
    report_path = target/'run/report.json'
    if report_path.is_file():
        pipeline = json.loads(report_path.read_text())
        proposal = pipeline.get('proposal_report',{})
        result.update(backend=proposal.get('backend', 'ollama'),status=pipeline['status'],measurement=pipeline.get('measurement'),
                      error=proposal.get('error',pipeline.get('error')),mode=proposal.get('mode'))
        result['generated_patch_validated'] = bool(exit_code==0 and pipeline['status']=='validation_passed'
            and proposal.get('mode')=='live_model' and (target/'review/index.html').is_file())
        result['runtime_validation'] = proposal.get('inventory_validation',
            proposal.get('telemetry_validation', proposal.get('pubsub_validation')))
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
            fields = ('id','model','provider','usage') if result.get('backend') in ('openrouter', 'nvidia') else (
                'done','done_reason','prompt_eval_count','eval_count','total_duration','load_duration','prompt_eval_duration','eval_duration')
            item['serving_counts']={key:raw.get(key) for key in fields}
        # Full memory samples remain in their original request-measurement artifacts.
        if 'measurement' in item:item['measurement']={key:value for key,value in item['measurement'].items() if key!='memory_samples'}
        requests.append(item)
    result['requests']=requests
    result['provider_errors'] = [
        dict(request=item['request'], http_status=item['measurement']['http_status'])
        for item in requests if item.get('measurement', {}).get('http_status')
    ]
    if result['provider_errors']:
        result['status'] = 'provider_unavailable'
    result['generated_patch_validated'] &= result['model_requests'] > 0
    return result


def execute(output,model,strategy='candidate_edits', *, full_benchmark=False, backend='ollama', cases=None):
    if strategy not in ('candidate_edits','candidate_blocks'):
        raise ValueError('live suite requires a supported live model strategy')
    if backend in ('openrouter', 'nvidia'):
        from importlib import import_module
        transport = import_module('patchgen.' + backend + '_client')
        credential = transport.credential
        if model != transport.MODEL:
            raise ValueError('Cloud evaluation requires its selected model')
        credential()
    elif backend != 'ollama' or model not in LOCAL_MODELS:
        raise ValueError('unsupported local backend or model')
    if cases is not None and (not cases or len(set(cases)) != len(cases) or not set(cases) <= set(CASES + ADDITIONAL_CASES)):
        raise ValueError('select distinct cases supported by the live route')
    output=check_output(output);output.mkdir(parents=True)
    available = manifest()
    plan = benchmark_plan(available) if full_benchmark else {name: 'eligible' for name in CASES}
    if cases:
        plan = benchmark_plan(available)
        plan = {name: 'not_selected' if state == 'eligible' and name not in cases else state
                for name, state in plan.items()}
    entries = [entry for entry in available if plan.get(entry['case']) == 'eligible']
    (output/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    (output/'manifest.json').write_text(json.dumps(entries,indent=2)+'\n')
    options = OPTIONS
    if backend in ('openrouter', 'nvidia'):
        options = transport.OPTIONS
    report=dict(status='running',mode='live_model',model=model,strategy=strategy,backend=backend,
                prompt_version=STRATEGY_VERSIONS[strategy],options=options,
                planned_cases=len(entries),automatic_repairs=0,human_approval_required=True,
                implementation_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                implementation_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
                scope='authored migrations eligible for actual model-generated runtime edits',
                benchmark_coverage=plan,
                benchmark_cases=len(available),
                timing_scope='per-request wall time includes local model load; prepared pipeline wall time separate; not propagation/human baseline',results=[])
    def save():(output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    for entry in entries:
        target=output/entry['case'];target.mkdir()
        command=[sys.executable,'-m','patchgen.pipeline','--fixture',str(ROOT/'patchgen/fixtures'/entry['profile']/'runtime-input.json'),
                 '--output',str(target/'run'),'--generate','--strategy',strategy,'--model',model,'--backend',backend,'--local-codegen',
                 '--review-output',str(target/'review')]
        start=time.monotonic()
        with (target/'pipeline.log').open('w') as log:
            try:code=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
            except OSError as error:log.write(str(error));code=1
        result=dict(case=entry['case'],**collect(target,code,time.monotonic()-start))
        report['results'].append(result);save()
        print(result['case']+': '+result['status']+'; actual model requests='+str(result['model_requests']),flush=True)
    passed=sum(r['generated_patch_validated'] for r in report['results'])
    unavailable = sum(row['status'] == 'provider_unavailable' for row in report['results'])
    report.update(status='provider_unavailable' if unavailable else 'completed',
                  provider_unavailable_cases=unavailable,validated_model_patches=passed,
                  model_patch_validation_rate=None if unavailable else passed/len(entries),
                  model_requests=sum(r['model_requests'] for r in report['results']),
                  generation_seconds=sum(r['generation_seconds'] for r in report['results']))
    save()
    return int(passed!=len(entries))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--full-benchmark', action='store_true',
                        help='record eligibility across the complete deterministic benchmark and run its supported live cases')
    parser.add_argument('--backend', choices=('ollama','openrouter','nvidia'), default='ollama')
    parser.add_argument('--model',choices=(*LOCAL_MODELS,OPENROUTER_MODEL,NVIDIA_MODEL), default=None)
    parser.add_argument('--case', choices=CASES+ADDITIONAL_CASES, action='append',
                        help='run selected cases as a smaller initial trial')
    parser.add_argument('--strategy',choices=('candidate_edits','candidate_blocks'),default='candidate_edits')
    args=parser.parse_args()
    model = args.model or ({'openrouter': OPENROUTER_MODEL, 'nvidia': NVIDIA_MODEL}.get(args.backend, 'ministral-3:8b'))
    try:
        return execute(args.output,model,args.strategy, full_benchmark=args.full_benchmark,
                       backend=args.backend,cases=args.case)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
