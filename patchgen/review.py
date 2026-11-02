"""Export portable local human-review evidence; never applies or merges a patch."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
from patchgen.generator import ContractError, PUBSUB_ARTIFACTS

ARTIFACTS = ('input.json','request.json','report.json','provenance.json','detector.json','locator.json',
             'measurement.json','implementation.json','proposal/report.json','proposal/assembly.json',
             'proposal/proposal.json','proposal/proposal.patch','proposal/validated.patch',
             'proposal/validation.log','proposal/validation-profile.json','proposal/validation-tests.patch')
PUBSUB_REVIEW_ARTIFACTS = tuple('proposal/pubsub/' + name for name in PUBSUB_ARTIFACTS) + tuple(
    'proposal/pubsub-harness/testbed/pubsub/' + name for name in ('run.py', 'broker.py', 'topics.json'))
ARTIFACTS += PUBSUB_REVIEW_ARTIFACTS
ASSETS = Path(__file__).with_name('review_assets')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact_path(root, name):
    # Names are either hardcoded export paths or untrusted manifest input.
    if not isinstance(name,str) or name not in ARTIFACTS:
        raise ContractError('unknown review artifact path')
    path = root/name
    if path.is_symlink() or root.resolve() not in path.resolve().parents:
        raise ContractError('review artifact escapes bundle')
    return path


def check_pubsub_evidence(root, report, available=None):
    """Passing pub/sub claims require the complete retained evaluator evidence."""
    mode = report.get('validation_profile', {}).get('pubsub_case')
    if not mode or report.get('status') != 'validation_passed':
        return
    if available is not None and not set(PUBSUB_REVIEW_ARTIFACTS) <= set(available):
        raise ContractError('passing pubsub review requires complete evidence')
    for name in PUBSUB_REVIEW_ARTIFACTS:
        if not artifact_path(root, name).is_file():
            raise ContractError('passing pubsub review requires complete evidence')
    result = json.loads(artifact_path(root, 'proposal/pubsub/report.json').read_text())
    if (result != report.get('pubsub_validation') or result.get('status') != 'passed' or result.get('case') != mode
            or result.get('runtime_revision') != report.get('source_revision') or result.get('decoded_deliveries') != 24
            or not result.get('children_stopped') or not result.get('broker_stopped')):
        raise ContractError('passing pubsub review has inconsistent validation evidence')
    for name in ('run.py', 'broker.py', 'topics.json'):
        actual = sha(artifact_path(root, 'proposal/pubsub-harness/testbed/pubsub/' + name).read_bytes())
        if actual != report.get('pubsub_harness_sha256', {}).get(name):
            raise ContractError('pubsub evaluator source hash mismatch')


def export(run, output):
    run, output = run.resolve(), output.resolve()
    if output == run or run in output.parents:
        raise ContractError('review output must be outside the source evidence directory')
    case_name = 'input.json' if (run/'input.json').exists() else 'request.json'
    report_name = 'proposal/report.json' if (run/'proposal/report.json').exists() else 'report.json'
    case = json.loads(artifact_path(run,case_name).read_text())
    report = json.loads(artifact_path(run,report_name).read_text())
    if report_name == 'report.json' and report.get('status') != 'rejected':
        raise ContractError('review without a proposal requires a rejected analysis report')
    if report.get('source_revision') != case.get('source_revision'):
        raise ContractError('review source revision mismatch')
    if not re.fullmatch(r'[0-9a-f]{40}',case.get('source_revision','')):
        raise ContractError('review requires exact source revision')
    passing = report_name == 'proposal/report.json' and report.get('status') == 'validation_passed'
    if passing and (not (run/'proposal/validated.patch').is_file() or not (run/'proposal/validated.patch').stat().st_size):
        raise ContractError('passing review requires the complete validated patch')
    check_pubsub_evidence(run, report)
    output.mkdir(parents=True,exist_ok=False)
    artifacts={}
    for name in ARTIFACTS:
        source=artifact_path(run,name)
        if source.is_file():
            destination=artifact_path(output/'artifacts',name)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)
            raw=destination.read_bytes()
            artifacts[name]=dict(sha256=sha(raw),bytes=len(raw))
    manifest=dict(review_version='1.0',change_id=case['change']['id'],source_revision=case['source_revision'],
                  input_artifact=case_name,report_artifact=report_name,
                  validation_status=report['status'],mode=report.get('mode','unknown'),strategy=report.get('strategy','unknown'),
                  approval_eligible=passing,human_approval_required=True,artifacts=artifacts,
                  limitations=['Validation applies to the retained testbed and checks only.',
                               'Decision records are self-reported, not authenticated signatures.',
                               'Review export and decisions never apply, merge or publish code.'])
    manifest_raw=(json.dumps(manifest,indent=2)+'\n').encode()
    (output/'manifest.json').write_bytes(manifest_raw)
    patch_name='proposal/validated.patch' if passing else 'proposal/proposal.patch'
    patch_path=output/'artifacts'/patch_name
    patch=patch_path.read_text() if patch_path.exists() else 'No patch was assembled. Inspect the rejection report.'
    diff='\n'.join('<span class="'+('add' if line.startswith('+') and not line.startswith('+++') else
                                  'del' if line.startswith('-') and not line.startswith('---') else
                                  'hunk' if line.startswith(('@@','diff ','+++','---')) else 'context')+'">'+html.escape(line)+'</span>' for line in patch.splitlines())
    links=''.join(f'<li><a href="artifacts/{name}" target="_blank" rel="noopener">{html.escape(name)}</a><span>{meta["bytes"]:,} bytes</span></li>' for name,meta in artifacts.items())
    payload=dict(manifest_sha256=sha(manifest_raw),manifest=manifest)
    replacements=dict(TITLE=html.escape(case['change']['id']),STATUS=html.escape(report['status']),
                      MODE=html.escape(report.get('mode','unknown')),STRATEGY=html.escape(report.get('strategy','unknown')),
                      REVISION=case['source_revision'],BEHAVIOR=html.escape(case['intended_behavior']),DIFF=diff,LINKS=links,
                      ELIGIBLE='true' if passing else 'false',
                      DATA=json.dumps(payload).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026'))
    page=(ASSETS/'review.html').read_text()
    page=re.sub(r'\{\{([A-Z]+)\}\}',lambda match:replacements[match.group(1)],page)
    (output/'index.html').write_text(page)
    shutil.copyfile(ASSETS/'review.css',output/'review.css')
    shutil.copyfile(ASSETS/'review.js',output/'review.js')
    return manifest


def verify(bundle, decision):
    bundle=bundle.resolve()
    raw=(bundle/'manifest.json').read_bytes()
    manifest=json.loads(raw)
    if manifest.get('review_version')!='1.0':
        raise ContractError('unsupported review manifest')
    record=json.loads(decision.read_text())
    if record.get('decision_version')!='1.0' or record.get('manifest_sha256')!=sha(raw):
        raise ContractError('decision manifest identity mismatch')
    if record.get('decision') not in ('approve','reject'):
        raise ContractError('unknown human decision')
    for name in ('reviewer','rationale','recorded_at'):
        if not isinstance(record.get(name),str) or not record[name].strip():
            raise ContractError('decision requires '+name)
    if record.get('reviewed_complete_bundle') is not True:
        raise ContractError('complete-bundle review acknowledgement missing')
    for key in ('source_revision','change_id'):
        if record.get(key)!=manifest.get(key):
            raise ContractError('decision '+key+' mismatch')
    artifacts=manifest.get('artifacts')
    case_name=manifest.get('input_artifact','input.json')
    report_name=manifest.get('report_artifact','proposal/report.json')
    if case_name not in ('input.json','request.json') or report_name not in ('report.json','proposal/report.json'):
        raise ContractError('unknown review input/report artifact')
    required={case_name,report_name,'report.json'}
    if not isinstance(artifacts,dict) or not required <= artifacts.keys():
        raise ContractError('review manifest missing required artifacts')
    for name,metadata in artifacts.items():
        content=artifact_path(bundle/'artifacts',name).read_bytes()
        if metadata.get('sha256')!=sha(content) or metadata.get('bytes')!=len(content):
            raise ContractError('review artifact changed: '+name)
    report=json.loads((bundle/'artifacts'/report_name).read_text())
    case=json.loads((bundle/'artifacts'/case_name).read_text())
    if report.get('source_revision')!=manifest['source_revision'] or case.get('source_revision')!=manifest['source_revision'] or case['change']['id']!=manifest['change_id']:
        raise ContractError('review metadata mismatch')
    check_pubsub_evidence(bundle/'artifacts', report, artifacts)
    if record['decision']=='approve' and (report_name != 'proposal/report.json' or not manifest.get('approval_eligible') or report.get('status')!='validation_passed'
                                         or 'proposal/validated.patch' not in artifacts):
        raise ContractError('approval requires passing validation and complete patch')
    return dict(status='verified',decision=record['decision'],reviewer=record['reviewer'],manifest_sha256=sha(raw),
                meaning='self-reported decision matches exported evidence; no code applied or identity authentication')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    export_parser=sub.add_parser('export');export_parser.add_argument('--run',type=Path,required=True);export_parser.add_argument('--output',type=Path,required=True)
    verify_parser=sub.add_parser('verify');verify_parser.add_argument('--bundle',type=Path,required=True);verify_parser.add_argument('--decision',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=export(args.run,args.output) if args.action=='export' else verify(args.bundle,args.decision)
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
