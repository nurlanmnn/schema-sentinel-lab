"""Policy for one pinned telemetry message rename."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = '665e06e11f912e592f39966443fc7c06f8b3b9ac'
CHANGE_ID = 'telemetry-message-rename'
EVENT = dict(category='message_renamed', old_message='simulation.telemetry.VehicleTelemetry',
             new_message='simulation.telemetry.GroundSpeedSample')
POLICY = ('Rename the generated message type to GroundSpeedSample. Preserve field names, wire bytes, '
          'observations, and the strict speeding threshold for the raw telemetry payload.')
ROLES = {
    'runtimes/python/telemetry_runtime.py': (5, 9, 10),
    'runtimes/typescript/telemetry.ts': (2, 8, 9),
    'runtimes/csharp/Telemetry.cs': (11, 12),
}


def verify_target(case):
    change = case['change']
    if (case['source_revision'] != REVISION or change['id'] != CHANGE_ID
            or change['category'] != EVENT['category']
            or change['schema_path'] != 'proto/telemetry/vehicle.proto' or case['intended_behavior'] != POLICY):
        raise ContractError('telemetry message rename requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('telemetry message rename requires exactly the supported standalone message rename')


def prepare(source, detector, locator):
    """Use the existing syntax scan for the pinned strategy."""
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != ['message symbol candidates only; generated type usage requires review']
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('telemetry message rename requires the expected candidate scope and no extra scan warnings')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope='pinned telemetry message rename',
                                     locator_status='partial')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('telemetry message rename requires its three pinned runtime files')
    change = case['change']
    diff = unified_diff(change['schema_path'], change['old_schema'], change['new_schema'])
    decisions = []
    for path, edits in ROLES.items():
        file = files[path]
        source = file['source_context']
        lines = source.splitlines(keepends=True)
        candidates = {line for pos in file['positions'] for line in range(pos['start_line'], pos['end_line'] + 1)}
        old, new = 'VehicleTelemetry', 'GroundSpeedSample'
        for line in edits:
            if line not in candidates or lines[line - 1].count(old) != 1:
                raise ContractError(f'unresolved telemetry message rename role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=list(edits),
                              unchanged_candidate_lines=sorted(candidates - set(edits))))
    save(output / 'assembly.json', dict(strategy='deterministic_telemetry_message_rename',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Update imports and type references while preserving raw telemetry wire behavior.',
        confidence=0, assumptions=['Exact adopted raw-payload source only.',
            'Type-name-dependent consumers require a coordinated API update.',
            'Confidence is unestimated. Human review required.']))
