"""Pinned telemetry wire-tag and JSON observation migrations."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = '665e06e11f912e592f39966443fc7c06f8b3b9ac'
ISSUE = 'metadata candidates only; wire or JSON policy requires review'
SCHEMA = 'proto/telemetry/vehicle.proto'
ROLES = {
    'runtimes/python/telemetry_runtime.py': (10, 11, 12),
    'runtimes/typescript/telemetry.ts': (9, 10, 11),
    'runtimes/csharp/Telemetry.cs': (12, 13, 14),
}
POLICIES = {
    'telemetry-tag-move': (
        dict(category='field_renumbered', new_field_number=7),
        'Move speed_mps to wire tag 7 and reserve tag 2. Preserve runtime observations and the strict threshold.',
    ),
    'telemetry-json-key': (
        dict(category='field_json_name_changed'),
        'Use groundSpeed as the external speed observation key. Preserve binary protobuf and the strict threshold.',
    ),
}
JSON_EDITS = {
    'runtimes/python/telemetry_runtime.py': (11, "'speed_mps':", "'groundSpeed':"),
    'runtimes/typescript/telemetry.ts': (10, 'speed_mps:', 'groundSpeed:'),
    'runtimes/csharp/Telemetry.cs': (13, '["speed_mps"]', '["groundSpeed"]'),
}


def policy(case):
    change = case['change']
    selection = POLICIES.get(change['id'])
    if case['source_revision'] != REVISION or change['schema_path'] != SCHEMA or not selection:
        raise ContractError('unknown pinned telemetry metadata migration')
    event, behavior = selection
    result = detect(change['old_schema'], change['new_schema'], SCHEMA, REVISION, change['id'], behavior)
    expected = dict(event, message='simulation.telemetry.VehicleTelemetry', field_number=2,
                    old_name='speed_mps', new_name='speed_mps')
    if (case['intended_behavior'] != behavior or change['category'] != event['category']
            or not matches_single_event(result, expected)):
        raise ContractError('telemetry metadata migration requires its exact descriptor event and policy')
    if change['id'] == 'telemetry-json-key' and result['events'][0]['new_field']['json_name'] != 'groundSpeed':
        raise ContractError('telemetry JSON observation key must be groundSpeed')
    return change['id']


def prepare(source, detector, locator):
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    selected = policy(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != [ISSUE]
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('telemetry metadata migration requires the expected candidate scope')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope=selected, locator_status='partial')


def propose(case, output):
    selected = policy(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('telemetry metadata migration requires three pinned runtime files')
    change = case['change']
    diff = unified_diff(SCHEMA, change['old_schema'], change['new_schema'])
    decisions = []
    for path, roles in ROLES.items():
        file = files[path]
        source = file['source_context']
        candidates = {line for pos in file['positions'] for line in range(pos['start_line'], pos['end_line'] + 1)}
        if not set(roles) <= candidates:
            raise ContractError(f'missing telemetry metadata role in {path}')
        edited = []
        if selected == 'telemetry-json-key':
            line, old, new = JSON_EDITS[path]
            lines = source.splitlines(keepends=True)
            if lines[line - 1].count(old) != 1:
                raise ContractError(f'unresolved telemetry JSON observation in {path}')
            lines[line - 1] = lines[line - 1].replace(old, new)
            diff += unified_diff(path, source, ''.join(lines))
            edited.append(line)
        decisions.append(dict(path=path, edited_lines=edited, candidate_lines=sorted(candidates)))
    save(output / 'assembly.json', dict(strategy='deterministic_telemetry_metadata',
                                       model_requests=0, decisions=decisions))
    assumption = ('Coordinate rollout and migrate persisted tag-2 bytes.' if selected == 'telemetry-tag-move'
                  else 'Coordinate clients that read the old JSON key.')
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale=case['intended_behavior'], confidence=0,
        assumptions=[assumption, 'Confidence is unestimated. Human review required.']))
