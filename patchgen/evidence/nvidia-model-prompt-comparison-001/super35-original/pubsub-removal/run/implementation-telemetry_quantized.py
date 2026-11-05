"""Policy for one pinned telemetry speed quantization."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, save, unified_diff, validate_output

REVISION = '665e06e11f912e592f39966443fc7c06f8b3b9ac'
CHANGE_ID = 'telemetry-speed-quantized'
EVENT = dict(category='field_type_changed', message='simulation.telemetry.VehicleTelemetry',
             field_number=2, old_name='speed_mps', new_name='speed_mps', old_type=2, new_type=5)
POLICY = ('Quantize finite request.speed to signed int32 meters per second. Clamp to the int32 '
          'range then truncate toward zero. Observe integer speed_mps, and compare decoded '
          'integer speed to the existing strict >30 threshold. Coordinate the incompatible wire change.')
ROLES = {
    'runtimes/python/telemetry_runtime.py': (
        (10, "speed_mps=request['speed']",
         "speed_mps=int(min(2_147_483_647, max(-2_147_483_648, request['speed'])))"),
    ),
    'runtimes/typescript/telemetry.ts': (
        (9, 'speedMps: request.speed',
         'speedMps: Math.trunc(Math.min(2_147_483_647, Math.max(-2_147_483_648, request.speed)))'),
    ),
    'runtimes/csharp/Telemetry.cs': (
        (12, '(float)request.Speed', '(int)Math.Clamp(request.Speed, int.MinValue, int.MaxValue)'),
    ),
}


def verify_target(case):
    change = case['change']
    if (case['source_revision'] != REVISION or change['id'] != CHANGE_ID
            or change['category'] != EVENT['category']
            or change['schema_path'] != 'proto/telemetry/vehicle.proto' or case['intended_behavior'] != POLICY):
        raise ContractError('quantization requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('quantization requires exactly the supported float-to-int32 change')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('speed quantization requires its three pinned runtime files')
    change = case['change']
    diff = unified_diff(change['schema_path'], change['old_schema'], change['new_schema'])
    decisions = []
    for path, edits in ROLES.items():
        file = files[path]
        source = file['source_context']
        lines = source.splitlines(keepends=True)
        candidates = {line for pos in file['positions'] for line in range(pos['start_line'], pos['end_line'] + 1)}
        for line, old, new in edits:
            if line not in candidates or lines[line - 1].count(old) != 1:
                raise ContractError(f'unresolved speed quantization role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              unchanged_candidate_lines=sorted(candidates - {line for line, _, _ in edits})))
    save(output / 'assembly.json', dict(strategy='deterministic_telemetry_quantized',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Quantize telemetry producers and keep the strict decoded-speed threshold.',
        confidence=0, assumptions=['Finite JSON producer values and exact adopted source only.',
            'Field 2 changes wire type. Mixed-version operation requires a separate rollout plan.',
            'Confidence is unestimated. Human review required.']))
