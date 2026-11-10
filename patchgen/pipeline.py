"""One-command independent descriptor -> syntax candidates -> adapter workflow."""
from patchgen.nvidia_client import MODEL as NVIDIA_MODEL, MODELS as NVIDIA_MODELS
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from patchgen.detector import detect
from patchgen.locator import locate
from patchgen.adapter import adapt, coverage
from patchgen.generator import command, save, ContractError, require, safe_path, VALIDATION_PROFILES, LOCAL_MODELS, OPENROUTER_MODEL, INVENTORY_EVOLUTION_STRATEGIES, FEEDBACK_STRATEGIES

ROOT = Path(__file__).resolve().parents[1]
# Source files hashed and copied into every run so its output records the exact code used.
IMPLEMENTATION_FILES = ('detector.py','locator.py','python_bindings.py','runtime_inventory.py','source_spellings.py','typescript_bindings.py','binding_analysis.py','pipeline.py','adapter.py','generator.py','anchor_edits.py','feedback_blocks.py','rename_tokens.py','rename_roles.py','type_utf8.py','remove_name.py','type_precision.py','telemetry_units.py','inventory_width.py','stock_release.py','inventory_presence.py','inventory_labels.py','inventory_reservation.py','telemetry_quantized.py','inventory_state_rename.py','telemetry_message_rename.py','telemetry_metadata.py','inventory_evolution.py','openrouter_client.py','nvidia_client.py')


def run(case, output, generate=False, response=None, strategy="candidate_edits", local_codegen=False, model="ministral-3:8b", feedback=None, backend="ollama"):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    implementation = dict(revision=command(['git','rev-parse','HEAD'],ROOT).strip(),
                          files={name:hashlib.sha256((ROOT/'patchgen'/name).read_bytes()).hexdigest()
                                 for name in IMPLEMENTATION_FILES})
    save(output/'implementation.json',implementation)
    for filename in IMPLEMENTATION_FILES:
        if filename == 'generator.py':
            continue  # hashed above, but not copied (historical run layout)
        (output/('implementation-'+filename)).write_bytes((ROOT/'patchgen'/filename).read_bytes())
    revision=require(case,'source_revision',str,'request')
    if not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ContractError('request requires exact source commit')
    change=require(case,'change',dict,'request')
    for key in ('id','old_schema','new_schema','schema_path'):
        require(change,key,str,'request.change')
    safe_path(change['schema_path'])
    require(case,'intended_behavior',str,'request')
    source = output / 'source'
    command(['git','worktree','add','--detach',str(source),case['source_revision']],ROOT)
    change = case['change']
    old = command(['git','show',case['source_revision']+':'+change['schema_path']],ROOT)
    if old != change['old_schema']:
        raise ContractError('old schema does not match exact source revision')
    save(output/'request.json', dict(source_revision=revision,
        change={key:change[key] for key in ('id','schema_path','old_schema','new_schema')},
        intended_behavior=case['intended_behavior']))
    detector = detect(old,change['new_schema'],change['schema_path'],case['source_revision'],change['id'],case['intended_behavior'])
    save(output/'detector.json',detector)
    anchor = None
    if strategy == 'deterministic_inventory_reservation':
        from patchgen.inventory_reservation import policy_anchor
        anchor = policy_anchor(detector)
    locator = locate(source, detector, added_field_policy_anchor=anchor)
    save(output/'locator.json',locator)
    # Expectations are consulted after production, never used by detector or locator.
    profile_name = 'entity-name-removal' if change['id'] == 'entity-name-removal-001' else change['id']
    reference = ROOT/'patchgen/reference'/profile_name/'expected.json'
    metrics = None
    if reference.exists():
        truth = json.loads(reference.read_text())
        if truth['runtime_sites'] and 'positions' in truth['runtime_sites'][0]:
            truth['runtime_sites'] = [dict(path=f['path'],lines=[p['start_line'] for p in f['positions']]) for f in truth['runtime_sites']]
        metrics = coverage(truth,locator)
        metrics['classification_correct'] = detector['change']['category'] == truth.get('category', 'field_removed' if profile_name == 'entity-name-removal' else None)
        save(output/'measurement.json',metrics)
    report = dict(status='adapted',implementation=implementation,measurement=metrics,human_approval_required=True,
                  source_revision=case['source_revision'],scope='runtime syntax candidates; no receiver-type or semantic completeness proof')
    try:
        if strategy in INVENTORY_EVOLUTION_STRATEGIES:
            from patchgen.inventory_evolution import prepare
            generated, provenance = prepare(source, detector, locator, INVENTORY_EVOLUTION_STRATEGIES[strategy])
        elif strategy == 'deterministic_telemetry_metadata':
            from patchgen.telemetry_metadata import prepare
            generated, provenance = prepare(source, detector, locator)
        elif strategy == 'deterministic_telemetry_message_rename':
            from patchgen.telemetry_message_rename import prepare
            generated, provenance = prepare(source, detector, locator)
        elif strategy == 'deterministic_inventory_state_rename':
            from patchgen.inventory_state_rename import prepare
            generated, provenance = prepare(source, detector, locator)
        elif strategy == 'deterministic_inventory_reservation':
            from patchgen.inventory_reservation import prepare
            generated, provenance = prepare(source, detector, locator)
        elif strategy == 'deterministic_inventory_labels':
            from patchgen.inventory_labels import prepare
            generated, provenance = prepare(source, detector, locator)
        elif strategy == 'deterministic_inventory_presence':
            from patchgen.inventory_presence import prepare
            generated, provenance = prepare(source, detector, locator)
        elif strategy == 'deterministic_inventory_stock_release':
            from patchgen.stock_release import prepare
            generated, provenance = prepare(source, detector, locator)
        else:
            generated, provenance = adapt(source,detector,locator)
    except ContractError as error:
        report.update(status='rejected',mode='analysis_rejected',strategy='not_run',error=str(error),
                      generation='not_run',validation='not_run',
                      rejected_stage='detector' if detector['status'] != 'complete' else
                                     'locator' if locator['status'] != 'complete' else 'adapter')
        save(output/'report.json',report)
        return report
    save(output/'input.json',generated)
    save(output/'provenance.json',provenance)
    if generate or response:
        args = [sys.executable,'-m','patchgen.generator','--source',str(source),'--fixture',str(output/'input.json'),
                '--output',str(output/'proposal'),'--strategy',strategy,'--model',model,'--backend',backend,'--validate']
        if local_codegen:
            args += ['--local-codegen']
        if profile_name in VALIDATION_PROFILES:
            args += ['--validation-profile',profile_name]
        if response:
            args += ['--response',str(response.resolve())]
        if feedback:
            args += ['--feedback',str(feedback.resolve())]
        with (output/'generation.log').open('w') as log:
            process = subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        report['proposal_exit_code'] = process.returncode
        proposal_report = output/'proposal/report.json'
        report['proposal_report'] = (json.loads(proposal_report.read_text()) if proposal_report.exists() else
                                     dict(status='failed', error='generator exited without report; see generation.log'))
        report['status'] = report['proposal_report']['status']
    save(output/'report.json',report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'patchgen/fixtures/entity-name-rename/runtime-input.json')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--model',choices=(*LOCAL_MODELS,OPENROUTER_MODEL,*NVIDIA_MODELS),default=None,help='explicit model identifier')
    parser.add_argument('--backend', choices=('ollama','openrouter','nvidia'),default='ollama')
    parser.add_argument('--local-codegen',action='store_true',help='explicit pinned local alternative to remote Buf plugins')
    parser.add_argument('--review-output',type=Path,help='export portable human-review evidence after a proposal run; must be outside pipeline output')
    parser.add_argument('--strategy',choices=(*INVENTORY_EVOLUTION_STRATEGIES,'deterministic_telemetry_metadata','deterministic_telemetry_message_rename','deterministic_inventory_state_rename','deterministic_telemetry_quantized','deterministic_inventory_reservation','deterministic_inventory_labels','deterministic_inventory_presence','deterministic_inventory_stock_release','deterministic_inventory_width','deterministic_inventory_zigzag','candidate_edits','candidate_semantic_edits','candidate_blocks','candidate_semantic_blocks','candidate_feedback_blocks','candidate_semantic_feedback_blocks','syntax_rename','syntax_rename_roles','deterministic_rename_roles','deterministic_utf8_v2','deterministic_remove_name_v1','deterministic_telemetry_precision','deterministic_telemetry_units'),default='candidate_edits')
    parser.add_argument('--feedback',type=Path,help='explicit feedback for a separately measured live feedback attempt')
    parser.add_argument('--response',type=Path,help='explicit offline evaluator replay, not model success')
    args = parser.parse_args()
    try:
        args.model = args.model or ({'openrouter': OPENROUTER_MODEL, 'nvidia': NVIDIA_MODEL}.get(args.backend, 'ministral-3:8b'))
        if args.backend in ('openrouter', 'nvidia'):
            from importlib import import_module
            transport = import_module('patchgen.' + args.backend + '_client')
            credential = transport.credential
            cloud_feedback = args.backend == 'nvidia' and args.strategy == 'candidate_semantic_feedback_blocks'
            if (not args.generate or args.response or (args.feedback and not cloud_feedback)
                    or args.model not in getattr(transport, 'MODELS', (transport.MODEL,))):
                raise ContractError('Cloud backend requires an explicit generation run for its selected model')
            credential()
        if (bool(args.feedback)!=(args.strategy in FEEDBACK_STRATEGIES)
                or args.feedback and (not args.generate or args.response)):
            raise ContractError('feedback requires the live feedback strategy and --generate')
        if args.review_output and not (args.generate or args.response):
            raise ContractError('--review-output requires --generate or --response')
        if args.review_output and (args.review_output.exists() or args.review_output.resolve() == args.output.resolve()
                                   or args.output.resolve() in args.review_output.resolve().parents):
            raise ContractError('review output must be new and outside pipeline output')
        report = run(json.loads(args.fixture.read_text()),args.output,args.generate,args.response,args.strategy,args.local_codegen,args.model,args.feedback,args.backend)
        if args.review_output:
            from patchgen.review import export
            export(args.output,args.review_output)
        print(json.dumps(report,indent=2))
        return int(report['status'] in ('failed','rejected'))
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        if args.output.exists() and not isinstance(error,FileExistsError):
            save(args.output/'error.json',dict(status='rejected',error=str(error)))
        print(str(error),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
