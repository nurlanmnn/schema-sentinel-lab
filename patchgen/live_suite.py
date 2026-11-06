"""Measure actual local LLM proposals on migrations supported by the live route."""
from patchgen.nvidia_client import MODEL as NVIDIA_MODEL, MODELS as NVIDIA_MODELS
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
# Decision 0041: the frozen configuration for subsequent live evaluations.
LOCKED_DECISION = '0041'
LOCKED_CONFIG = dict(backend='nvidia', model='google/gemma-4-31b-it', strategy='candidate_semantic_blocks')


# Every authored benchmark case informed prompt development. Held-out cases come only from a
# sealed registry (patchgen/held_out.py) and never join run_benchmark.CASES.
# Fixed synthetic input: the hash changes only when prompt construction changes.
_FINGERPRINT_FILE = dict(path='runtimes/python/main.py', language='python', source_context='old = 1\n',
                         positions=[dict(start_line=1, end_line=1, reason='candidate')])
_FINGERPRINT_CASE = dict(contract_version='1.0', source_revision='0'*40, intended_behavior='fingerprint',
    change=dict(id='fingerprint', category='field_renamed', old_schema='a', new_schema='b', schema_path='proto/a.proto'),
    affected_files=[_FINGERPRINT_FILE])
LOCKED_PROMPT_SHA256 = dict(
    one_shot='9546791889d0d9ecd8a2baca015ce47a2740e0d179bdd92263dd55ac2d81cb23',
    repair='35dca82e6243080d902eeeb61963eb63a57350755f08fe476b31d216845204cb',
    protocol='b6fa35136a3155377f0ae887d29d8bd6dcbef0617d350a08872078f9a4fb6487')


def prompt_fingerprints():
    """Hash the locked prompts, edit resolver, envelope parser and sampling so silent tuning is detectable."""
    import inspect
    from patchgen import anchor_edits, generator, nvidia_client
    from patchgen.feedback_blocks import make_prompt as repair_prompt
    # A second file exercises the binding-specific prompt branch.
    bound = dict(_FINGERPRINT_FILE, path='runtimes/typescript/main.ts', language='typescript',
                 positions=[dict(start_line=1, end_line=1, reason='candidate', required_reference=True)])
    case = dict(_FINGERPRINT_CASE, affected_files=[_FINGERPRINT_FILE, bound])
    feedback = dict(case, model_feedback=dict(source_revision='0'*40, change_id='fingerprint',
        files={file['path']: dict(previous_response={}, validation_diagnostics=['fingerprint']) for file in (_FINGERPRINT_FILE, bound)}))
    digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    protocol = [inspect.getsource(function) for function in (generator.prompt, generator.file_context, anchor_edits.candidates,
                anchor_edits.resolve, nvidia_client.parse_content)] + [nvidia_client.options_for(LOCKED_CONFIG['model'])]
    return dict(one_shot=digest([anchor_edits.make_prompt(case, file, semantic=True)[0] for file in (_FINGERPRINT_FILE, bound)]),
                repair=digest([repair_prompt(feedback, file, semantic=True)[0] for file in (_FINGERPRINT_FILE, bound)]),
                protocol=digest(protocol))


def require_locked_prompts():
    if prompt_fingerprints() != LOCKED_PROMPT_SHA256:
        raise ValueError('locked prompt text changed; record a new decision before a locked run')


def held_out_cohorts(registry):
    """Case names per reported cohort. Variants are kept out of the headline because they correlate with parents."""
    cases = registry['cases']
    base = [c for c in cases if not c.get('variant_of')]
    return dict(headline=[c['case'] for c in base],
                **{label: [c['case'] for c in base if c['label'] == label] for label in ('new_mechanism', 'transfer')},
                minimal_semantics_variants=[c['case'] for c in cases if c.get('variant_of')])


def held_out_entries(registry):
    """Manifest rows for sealed cases, read from their sealed fixtures, plus withdrawn case names."""
    entries, withdrawn = [], {}
    for case in registry['cases']:
        if case['status'] == 'withdrawn':
            withdrawn[case['case']] = case['withdrawn_reason']
            continue
        fixture = ROOT/'patchgen/fixtures'/case['profile']/'runtime-input.json'
        entries.append(dict(case=case['case'], id=case['id'], label=case['label'], variant_of=case.get('variant_of'),
                            profile=case['profile'], source_revision=json.loads(fixture.read_text())['source_revision'],
                            fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest()))
    return entries, withdrawn


def resolve_configuration(args):
    """Apply --locked, refusing partial overrides so the frozen setup stays exact."""
    if args.locked:
        if args.backend or args.model or args.strategy:
            raise ValueError('--locked fixes backend, model and strategy; omit those options')
        return dict(LOCKED_CONFIG)
    backend = args.backend or 'ollama'
    model = args.model or ({'openrouter': OPENROUTER_MODEL, 'nvidia': NVIDIA_MODEL}.get(backend, 'ministral-3:8b'))
    return dict(backend=backend, model=model, strategy=args.strategy or 'candidate_edits')


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
    result['provider_errors'] += [dict(request=item['request'], status='provider_identity_mismatch')
        for item in requests if item.get('measurement', {}).get('status') == 'provider_identity_mismatch']
    if result['provider_errors']:
        result['status'] = 'provider_unavailable'
    result['generated_patch_validated'] &= result['model_requests'] > 0
    return result


def execute(output,model,strategy='candidate_edits', *, full_benchmark=False, backend='ollama', cases=None, locked=False,
            held_out=None, rerun_reason=None):
    if locked and dict(backend=backend, model=model, strategy=strategy) != LOCKED_CONFIG:
        raise ValueError('locked run must use the decision 0041 configuration')
    if locked:
        require_locked_prompts()
    registry = None
    if held_out is not None:
        from patchgen import held_out as sealed
        if not locked or cases or full_benchmark:
            raise ValueError('a held-out run requires --locked and cannot select development cases')
        # Verify before any credential or network use; a mismatch must never reach the model.
        registry = sealed.verify(held_out)
    elif rerun_reason:
        raise ValueError('--rerun-reason applies only to held-out runs')
    if strategy not in ('candidate_edits','candidate_semantic_edits','candidate_blocks','candidate_semantic_blocks'):
        raise ValueError('live suite requires a supported live model strategy')
    if backend in ('openrouter', 'nvidia'):
        from importlib import import_module
        transport = import_module('patchgen.' + backend + '_client')
        credential = transport.credential
        if model not in getattr(transport, 'MODELS', (transport.MODEL,)):
            raise ValueError('Cloud evaluation requires its selected model')
        credential()
    elif backend != 'ollama' or model not in LOCAL_MODELS:
        raise ValueError('unsupported local backend or model')
    if cases is not None and (not cases or len(set(cases)) != len(cases) or not set(cases) <= set(CASES + ADDITIONAL_CASES)):
        raise ValueError('select distinct cases supported by the live route')
    output=check_output(output)
    withdrawn, attempt = {}, None
    if registry:
        # Recorded before the output exists or any request is sent, wherever the output lives.
        attempt = sealed.begin_one_shot(held_out, output, rerun_reason)
    output.mkdir(parents=True)
    if registry:
        entries, withdrawn = held_out_entries(registry)
        available = entries
        plan = {**{entry['case']: 'eligible' for entry in entries}, **{name: 'withdrawn' for name in withdrawn}}
    else:
        available = manifest()
        plan = benchmark_plan(available) if full_benchmark else {name: 'eligible' for name in CASES}
        if cases:
            plan = benchmark_plan(available)
            plan = {name: 'not_selected' if state == 'eligible' and name not in cases else state
                    for name, state in plan.items()}
        entries = [entry for entry in available if plan.get(entry['case']) == 'eligible']
    splits = {entry['case']: 'held_out' if registry else 'development' for entry in entries}
    (output/'runner-source.py').write_bytes(Path(__file__).read_bytes())
    (output/'manifest.json').write_text(json.dumps(entries,indent=2)+'\n')
    options = OPTIONS
    if backend in ('openrouter', 'nvidia'):
        options = transport.options_for(model) if hasattr(transport, 'options_for') else transport.OPTIONS
    report=dict(status='running',mode='live_model',model=model,strategy=strategy,backend=backend,
                prompt_version=STRATEGY_VERSIONS[strategy],options=options,
                locked_configuration=LOCKED_DECISION if locked else None,
                prompt_fingerprints=prompt_fingerprints() if locked else None,
                case_split=splits,
                held_out_registry=str(Path(held_out).resolve().relative_to(ROOT)) if registry else None,
                held_out_registry_sha256=hashlib.sha256(Path(held_out).read_bytes()).hexdigest() if registry else None,
                held_out_attempt=attempt['attempt'] if attempt else None,
                cohorts=held_out_cohorts(registry) if registry else None,
                case_labels={entry['case']: entry['label'] for entry in entries} if registry else None,
                withdrawn_cases=withdrawn if registry else None,
                rerun_reason=rerun_reason,
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
        if result['status'] == 'provider_unavailable':
            break
    passed=sum(r['generated_patch_validated'] for r in report['results'])
    unavailable = sum(row['status'] == 'provider_unavailable' for row in report['results'])
    count = lambda rows: f"{sum(r['generated_patch_validated'] for r in rows)}/{len(rows)}"
    denominator = len(entries)
    if registry:
        # Every denominator comes from the registry: withdrawn and unattempted cases count as unvalidated.
        validated = {r['case'] for r in report['results'] if r['generated_patch_validated']}
        scored = {name: f"{len(validated & set(names))}/{len(names)}" for name, names in report['cohorts'].items()}
        headline = report['cohorts']['headline']
        passed, denominator = len(validated & set(headline)), len(headline)
        report.update(validated_by_cohort=scored, headline_validated=scored['headline'])
    report.update(status='provider_unavailable' if unavailable else 'completed',
                  provider_unavailable_cases=unavailable,validated_model_patches=passed,
                  model_patch_validation_rate=None if unavailable or not denominator else passed/denominator,
                  validated_by_split={split: count([r for r in report['results'] if splits[r['case']] == split])
                                      for split in ('development', 'held_out')},
                  model_requests=sum(r['model_requests'] for r in report['results']),
                  generation_seconds=sum(r['generation_seconds'] for r in report['results']))
    save()
    if registry:
        sealed.finish(held_out, attempt['attempt'], output)
    return int(passed!=denominator)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--full-benchmark', action='store_true',
                        help='record eligibility across the complete deterministic benchmark and run its supported live cases')
    parser.add_argument('--locked', action='store_true',
                        help='use the decision 0041 configuration: Gemma 4 31B via NVIDIA, semantic blocks 3.1')
    parser.add_argument('--backend', choices=('ollama','openrouter','nvidia'), default=None)
    parser.add_argument('--model',choices=(*LOCAL_MODELS,OPENROUTER_MODEL,*NVIDIA_MODELS), default=None)
    parser.add_argument('--case', choices=CASES+ADDITIONAL_CASES, action='append',
                        help='run selected cases as a smaller initial trial')
    parser.add_argument('--strategy',choices=('candidate_edits','candidate_semantic_edits','candidate_blocks','candidate_semantic_blocks'),default=None)
    parser.add_argument('--held-out', type=Path, help='sealed held-out registry; requires --locked')
    parser.add_argument('--rerun-reason', help='record a separate, non-substituting rerun of already-scored held-out cases')
    args=parser.parse_args()
    try:
        config = resolve_configuration(args)
        return execute(args.output,config['model'],config['strategy'], full_benchmark=args.full_benchmark,
                       backend=config['backend'],cases=args.case,locked=args.locked,
                       held_out=args.held_out, rerun_reason=args.rerun_reason)
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
