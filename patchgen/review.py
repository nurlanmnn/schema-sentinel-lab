"""Export portable local human-review evidence; never applies or merges a patch."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
from patchgen.generator import ContractError, INVENTORY_STRATEGIES, PUBSUB_ARTIFACTS
from testbed.inventory.run import ARTIFACTS as INVENTORY_FILES, check_results as inventory_check, expected as inventory_expected, requests as inventory_requests
from testbed.telemetry.run import ARTIFACTS as TELEMETRY_FILES, VALIDATION_COUNTS, check_results, expected, requests

ARTIFACTS = ('input.json','request.json','report.json','provenance.json','detector.json','locator.json',
             'measurement.json','implementation.json','proposal/report.json','proposal/assembly.json',
             'proposal/inventory-width-source.py','proposal/inventory-zigzag-source.py','proposal/inventory-stock-release-source.py','proposal/inventory-presence-source.py','proposal/inventory-labels-source.py','proposal/inventory-reservation-source.py','proposal/inventory-packed-bins-source.py','proposal/inventory-routing-oneof-source.py','proposal/inventory-state-retirement-source.py','proposal/inventory-state-rename-source.py','proposal/proposal.json','proposal/proposal.patch','proposal/validated.patch','proposal/type-precision-source.py','proposal/telemetry-units-source.py','proposal/telemetry-quantized-source.py','proposal/telemetry-message-rename-source.py','proposal/telemetry-metadata-source.py','proposal/openrouter-client-source.py','proposal/nvidia-client-source.py',
             'proposal/validation.log','proposal/validation-profile.json','proposal/validation-tests.patch')
PUBSUB_REVIEW_ARTIFACTS = tuple('proposal/pubsub/' + name for name in PUBSUB_ARTIFACTS) + tuple(
    'proposal/pubsub-harness/testbed/pubsub/' + name for name in ('run.py', 'broker.py', 'topics.json'))
PUBSUB_NEGATIVE_ARTIFACTS = tuple('proposal/pubsub-malformed/' + name for name in PUBSUB_ARTIFACTS)
TELEMETRY_ARTIFACTS = tuple('proposal/telemetry/'+name for name in TELEMETRY_FILES) + ('proposal/telemetry-oracle-source.py',)
LOCAL_CODEGEN_ARTIFACTS = ('proposal/local-codegen-source.py', 'proposal/local-codegen-toolchain.json')
INVENTORY_ARTIFACTS = tuple('proposal/inventory/'+name for name in INVENTORY_FILES) + ('proposal/inventory-oracle-source.py',)
ARTIFACTS += INVENTORY_ARTIFACTS + PUBSUB_REVIEW_ARTIFACTS + PUBSUB_NEGATIVE_ARTIFACTS + TELEMETRY_ARTIFACTS + LOCAL_CODEGEN_ARTIFACTS
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
    if report.get('validation_profile', {}).get('pubsub_negative_control'):
        if available is not None and not set(PUBSUB_NEGATIVE_ARTIFACTS) <= set(available):
            raise ContractError('pubsub review requires negative-control evidence')
        for name in PUBSUB_NEGATIVE_ARTIFACTS:
            if not artifact_path(root, name).is_file():
                raise ContractError('pubsub review requires negative-control evidence')
        rejected = json.loads(artifact_path(root, 'proposal/pubsub-malformed/report.json').read_text())
        codes = rejected.get('subscriber_exit_codes', {})
        decoder_failures = rejected.get('decoder_failures', {})
        if (rejected != report.get('pubsub_negative_control') or rejected.get('status') != 'expected_rejection_observed'
                or rejected.get('scenario') != 'malformed' or rejected.get('case') != mode
                or rejected.get('runtime_revision') != report.get('source_revision') or rejected.get('decoded_deliveries') != 0
                or not rejected.get('children_stopped') or not rejected.get('broker_stopped')
                or (report['validation_profile']['pubsub_negative_control'] == 'truncated_v1_decoder_logs'
                    and (set(decoder_failures) != {'python', 'typescript', 'csharp'} or any(value is not True for value in decoder_failures.values())))
                or set(codes) != {'python', 'typescript', 'csharp'} or any(type(code) is not int or code == 0 for code in codes.values())):
            raise ContractError('pubsub review has inconsistent negative-control evidence')


def check_host_evidence(root, report, available=None):
    if report.get('status') != 'validation_passed':
        return
    def required(names):
        if available is not None and not set(names) <= set(available):
            raise ContractError('passing review requires complete host evidence')
        if any(not artifact_path(root,name).is_file() for name in names):
            raise ContractError('passing review requires complete host evidence')
    inventory_strategy = INVENTORY_STRATEGIES.get(report.get('strategy'))
    if inventory_strategy:
        if report.get('validation_profile', {}).get('inventory_case') != inventory_strategy:
            raise ContractError('passing inventory review requires the matching validation profile')
        policy_path = f'proposal/inventory-{inventory_strategy}-source.py'
        required((policy_path,))
        if sha(artifact_path(root, policy_path).read_bytes()) != report.get(f'inventory_{inventory_strategy}_sha256'):
            raise ContractError('inventory migration policy source hash mismatch')
    if report.get('strategy') in ('deterministic_telemetry_precision','deterministic_telemetry_units'):
        required(('proposal/type-precision-source.py',))
        if sha(artifact_path(root,'proposal/type-precision-source.py').read_bytes()) != report.get('type_precision_sha256'):
            raise ContractError('precision policy source hash mismatch')
    if report.get('strategy') == 'deterministic_telemetry_units':
        required(('proposal/telemetry-units-source.py',))
        if sha(artifact_path(root,'proposal/telemetry-units-source.py').read_bytes()) != report.get('telemetry_units_sha256'):
            raise ContractError('units policy source hash mismatch')
    if report.get('strategy') == 'deterministic_telemetry_quantized':
        path = 'proposal/telemetry-quantized-source.py'
        required((path,))
        if (sha(artifact_path(root, path).read_bytes()) != report.get('telemetry_quantized_sha256')
                or report.get('validation_profile', {}).get('telemetry_case') != 'quantized'):
            raise ContractError('quantization policy or validation profile mismatch')
    if report.get('strategy') == 'deterministic_telemetry_message_rename':
        path = 'proposal/telemetry-message-rename-source.py'
        required((path,))
        if (sha(artifact_path(root, path).read_bytes()) != report.get('telemetry_message_rename_sha256')
                or report.get('validation_profile', {}).get('telemetry_case') != 'message-rename'):
            raise ContractError('message rename policy or validation profile mismatch')
    if report.get('strategy') == 'deterministic_telemetry_metadata':
        path = 'proposal/telemetry-metadata-source.py'
        required((path,))
        if (sha(artifact_path(root, path).read_bytes()) != report.get('telemetry_metadata_sha256')
                or report.get('validation_profile', {}).get('telemetry_case') not in ('tag-move', 'json-key')):
            raise ContractError('telemetry metadata policy or validation profile mismatch')
    if report.get('backend') in ('openrouter', 'nvidia'):
        backend = report['backend']
        path = 'proposal/' + backend + '-client-source.py'
        required((path,))
        if sha(artifact_path(root, path).read_bytes()) != report.get(backend + '_client_sha256'):
            raise ContractError('Cloud transport source hash mismatch')
    if report.get('codegen') == 'local_pinned':
        required(LOCAL_CODEGEN_ARTIFACTS)
        tools = json.loads(artifact_path(root,'proposal/local-codegen-toolchain.json').read_text())
        if (sha(artifact_path(root,'proposal/local-codegen-source.py').read_bytes()) != report.get('local_codegen_sha256')
                or tools != report.get('local_codegen_toolchain') or tools.get('protoc_version') != 'libprotoc 25.1'
                or tools.get('ts_proto_version') != '1.165.0'):
            raise ContractError('local codegen evidence mismatch')
    if report.get('validation_profile',{}).get('inventory_case'):
        required(INVENTORY_ARTIFACTS)
        mode = report['validation_profile']['inventory_case']
        if mode not in INVENTORY_STRATEGIES.values() or inventory_strategy and mode != inventory_strategy:
            raise ContractError('unknown or inconsistent inventory review mode')
        result = json.loads(artifact_path(root,'proposal/inventory/report.json').read_text())
        if (result != report.get('inventory_validation') or result.get('status') != 'passed'
                or result.get('case') != mode or result.get('runtime_cases') != 48
                or result.get('runtime_revision') != report.get('source_revision')
                or sha(artifact_path(root,'proposal/inventory-oracle-source.py').read_bytes()) != report.get('inventory_oracle_sha256')):
            raise ContractError('inventory review has inconsistent validation evidence')
        retained = json.loads(artifact_path(root,'proposal/inventory/expected.json').read_text())
        if retained != dict(requests=inventory_requests(mode),results=inventory_expected(mode)):
            raise ContractError('inventory review has inconsistent expected cases')
        for runtime in ('python','typescript','csharp'):
            record = json.loads(artifact_path(root,'proposal/inventory/'+runtime+'.json').read_text())
            try:
                if type(record.get('exit_code')) is not int or record['exit_code'] != 0:
                    raise ValueError('runtime did not exit successfully')
                inventory_check(json.loads(record['stdout']),inventory_expected(mode))
            except (KeyError,ValueError) as error:
                raise ContractError('inventory runtime evidence mismatch') from error
    if report.get('validation_profile',{}).get('telemetry_case'):
        required(TELEMETRY_ARTIFACTS)
        mode = report['validation_profile']['telemetry_case']
        if mode not in VALIDATION_COUNTS:
            raise ContractError('unknown telemetry review mode')
        result = json.loads(artifact_path(root,'proposal/telemetry/report.json').read_text())
        if (result != report.get('telemetry_validation') or result.get('status') != 'passed'
                or result.get('case') != mode or result.get('runtime_cases') != VALIDATION_COUNTS[mode]
                or result.get('runtime_revision') != report.get('source_revision')
                or sha(artifact_path(root,'proposal/telemetry-oracle-source.py').read_bytes()) != report.get('telemetry_oracle_sha256')):
            raise ContractError('telemetry review has inconsistent validation evidence')
        retained = json.loads(artifact_path(root,'proposal/telemetry/expected.json').read_text())
        if retained != dict(requests=requests(mode),results=expected(mode)):
            raise ContractError('telemetry review has inconsistent expected cases')
        for runtime in ('python','typescript','csharp'):
            record = json.loads(artifact_path(root,'proposal/telemetry/'+runtime+'.json').read_text())
            try:
                if type(record.get('exit_code')) is not int or record['exit_code'] != 0:
                    raise ValueError('runtime did not exit successfully')
                check_results(json.loads(record['stdout']),expected(mode))
            except (KeyError,ValueError) as error:
                raise ContractError('telemetry runtime evidence mismatch') from error


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
    check_host_evidence(run, report)
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
    check_host_evidence(bundle/'artifacts', report, artifacts)
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
