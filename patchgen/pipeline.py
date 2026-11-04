"""One-command independent descriptor -> syntax candidates -> adapter workflow."""
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
from patchgen.generator import command, save, ContractError, require, safe_path, VALIDATION_PROFILES, LOCAL_MODELS

ROOT = Path(__file__).resolve().parents[1]


def run(case, output, generate=False, response=None, strategy="candidate_edits", local_codegen=False, model="ministral-3:8b", feedback=None):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    implementation = dict(revision=command(['git','rev-parse','HEAD'],ROOT).strip(),
                          files={name:hashlib.sha256((ROOT/'patchgen'/name).read_bytes()).hexdigest()
                                 for name in ('detector.py','locator.py','python_bindings.py','runtime_inventory.py','source_spellings.py','typescript_bindings.py','binding_analysis.py','pipeline.py','adapter.py','generator.py','anchor_edits.py','feedback_blocks.py','rename_tokens.py','rename_roles.py','type_utf8.py','remove_name.py','type_precision.py','telemetry_units.py','inventory_width.py')})
    save(output/'implementation.json',implementation)
    for filename in ('detector.py','locator.py','python_bindings.py','runtime_inventory.py','source_spellings.py','typescript_bindings.py','binding_analysis.py','pipeline.py','adapter.py','anchor_edits.py','feedback_blocks.py','rename_tokens.py','rename_roles.py','type_utf8.py','remove_name.py','type_precision.py','telemetry_units.py','inventory_width.py'):
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
    locator = locate(source,detector)
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
                '--output',str(output/'proposal'),'--strategy',strategy,'--model',model,'--validate']
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
    parser.add_argument('--model',choices=LOCAL_MODELS,default='ministral-3:8b',help='installed local model only; does not download models')
    parser.add_argument('--local-codegen',action='store_true',help='explicit pinned local alternative to remote Buf plugins')
    parser.add_argument('--review-output',type=Path,help='export portable human-review evidence after a proposal run; must be outside pipeline output')
    parser.add_argument('--strategy',choices=('deterministic_inventory_width','deterministic_inventory_zigzag','candidate_edits','candidate_blocks','candidate_feedback_blocks','syntax_rename','syntax_rename_roles','deterministic_rename_roles','deterministic_utf8_v2','deterministic_remove_name_v1','deterministic_telemetry_precision','deterministic_telemetry_units'),default='candidate_edits')
    parser.add_argument('--feedback',type=Path,help='explicit feedback for a separately measured live feedback attempt')
    parser.add_argument('--response',type=Path,help='explicit offline evaluator replay, not model success')
    args = parser.parse_args()
    try:
        if (bool(args.feedback)!=(args.strategy=='candidate_feedback_blocks')
                or args.feedback and (not args.generate or args.response)):
            raise ContractError('feedback requires the live feedback strategy and --generate')
        if args.review_output and not (args.generate or args.response):
            raise ContractError('--review-output requires --generate or --response')
        if args.review_output and (args.review_output.exists() or args.review_output.resolve() == args.output.resolve()
                                   or args.output.resolve() in args.review_output.resolve().parents):
            raise ContractError('review output must be new and outside pipeline output')
        report = run(json.loads(args.fixture.read_text()),args.output,args.generate,args.response,args.strategy,args.local_codegen,args.model,args.feedback)
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
