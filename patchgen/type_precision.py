"""Bounded telemetry float32 -> float64 proposal; no model or reference answer.

Only the adopted direct generated-binding construction/observation/threshold
shapes are accepted. This is not general receiver, alias or units resolution.
"""
from tree_sitter import Language, Parser
from patchgen.locator import FACTORIES, walk
from patchgen.detector import detect, descriptor, matches_single_event
from patchgen.type_utf8 import compact
from patchgen.generator import ContractError, save, unified_diff, validate_output


def target(case):
    change = case['change']
    result = detect(change['old_schema'],change['new_schema'],change['schema_path'],
                    case['source_revision'],change['id'],case['intended_behavior'])
    wanted = dict(category='field_type_changed',message='simulation.telemetry.VehicleTelemetry',field_number=2,
                  old_name='speed_mps',new_name='speed_mps',old_type=2,new_type=1)
    if not matches_single_event(result, wanted):
        raise ContractError('precision policy only supports VehicleTelemetry.speed_mps float->double field 2')
    file, _ = descriptor(change['new_schema'],change['schema_path'])
    field = next(f for m in file.message_type if m.name=='VehicleTelemetry' for f in m.field if f.number==2)
    if field.label != 1 or field.proto3_optional or field.HasField('oneof_index'):
        raise ContractError('precision policy requires non-optional singular field outside oneof')
    if 'Preserve meters per second and strict >30' not in case['intended_behavior']:
        raise ContractError('precision policy requires explicit units and threshold preservation')


SHAPES = {
    'python': [
        "sample = VehicleTelemetry(vehicle_id=request['vehicle_id'], speed_mps=request['speed'])",
        "fields = {'vehicle_id': entity.vehicle_id, 'speed_mps': entity.speed_mps}",
        "return {'fields': fields, 'speeding': entity.speed_mps > 30.0,"],
    'typescript': [
        'const sample = VehicleTelemetry.encode({ vehicleId: request.vehicle_id, speedMps: request.speed }).finish();',
        'const fields = { vehicle_id: entity.vehicleId, speed_mps: entity.speedMps };',
        'return { fields, speeding: entity.speedMps > 30.0, constructed_payload: Buffer.from(sample).toString("base64") };'],
    'csharp': [
        'var sample = new Simulation.Telemetry.VehicleTelemetry { VehicleId = request.VehicleId, SpeedMps = (float)request.Speed };',
        'var fields = new Dictionary<string, object> { ["vehicle_id"] = entity.VehicleId, ["speed_mps"] = entity.SpeedMps };',
        'return new { fields, speeding = entity.SpeedMps > 30.0, constructed_payload = Convert.ToBase64String(sample.ToByteArray()) };'],
}
# These are source syntax fragments, not strings found in comments or literals.
BINDINGS = {
    'python': [
        ('import_from_statement','from telemetry.vehicle_pb2 import VehicleTelemetry'),
        ('assignment',"entity = VehicleTelemetry.FromString(base64.b64decode(request['payload'], validate=True))")],
    'typescript': [
        ('import_statement','import { VehicleTelemetry } from "../../generated/ts/telemetry/vehicle";'),
        ('lexical_declaration','const entity = VehicleTelemetry.decode(new Uint8Array(Buffer.from(request.payload, "base64")));')],
    'csharp': [
        ('local_declaration_statement','var entity = Simulation.Telemetry.VehicleTelemetry.Parser.ParseFrom(Convert.FromBase64String(request.Payload));'),
        ('record_declaration','record TelemetryRequest(string Payload, [property: System.Text.Json.Serialization.JsonPropertyName("vehicle_id")] string VehicleId, double Speed);')],
}


def inspect_shapes(file):
    language = file['language']
    if language not in SHAPES:
        raise ContractError('unsupported precision language')
    raw = file['source_context'].encode()
    tree = Parser(Language(FACTORIES[language]())).parse(raw)
    if tree.root_node.has_error:
        raise ContractError('precision source parse error')
    nodes = list(walk(tree.root_node))
    text = lambda n: raw[n.start_byte:n.end_byte].decode()
    for kind, expected in BINDINGS[language]:
        matching = [n for n in nodes if n.type==kind and compact(text(n))==compact(expected)]
        if len(matching) != 1:
            raise ContractError('unsupported or duplicate precision generated binding')
    candidates = {n for p in file['positions'] for n in range(p['start_line'],p['end_line']+1)}
    lines = raw.decode().splitlines()
    wanted = {compact(line) for line in SHAPES[language]}
    if len(candidates)!=3 or {compact(lines[n-1]) for n in candidates} != wanted:
        raise ContractError('unresolved precision candidate roles')
    # Reject a matching candidate hidden entirely in a multiline comment/string.
    for line in candidates:
        if not any(n.start_point.row+1==line and n.type in (
                'assignment','return_statement','lexical_declaration','local_declaration_statement') for n in nodes):
            raise ContractError('precision candidate must be executable syntax')
    return raw, nodes, candidates


def transform(file):
    raw, nodes, candidates = inspect_shapes(file)
    text = lambda n: raw[n.start_byte:n.end_byte].decode()
    language = file['language']
    edits = []
    if language == 'csharp':
        casts = [n for n in nodes if n.type=='cast_expression' and text(n)=='(float)request.Speed']
        if len(casts)!=1 or casts[0].start_point.row+1 not in candidates:
            raise ContractError('unsupported precision narrowing cast')
        node = casts[0]
        edits.append(dict(start_byte=node.start_byte,end_byte=node.end_byte,before=text(node),after='request.Speed'))
        raw = raw[:node.start_byte]+b'request.Speed'+raw[node.end_byte:]
    return raw.decode(), dict(candidate_lines=sorted(candidates),edits=edits,
        policy='Python float and TS number already binary64; C# generated property widens; remove explicit narrowing cast')


def propose(case, output):
    target(case)
    if {file['language'] for file in case['affected_files']} != set(SHAPES) or len(case['affected_files']) != 3:
        raise ContractError('precision policy requires exactly three adopted runtime files')
    diff = unified_diff(case['change']['schema_path'],case['change']['old_schema'],case['change']['new_schema'])
    for index,file in enumerate(case['affected_files'],1):
        updated,evidence = transform(file)
        directory=output/'deterministic'/f'{index:02d}';directory.mkdir(parents=True,exist_ok=False)
        save(directory/'precision-decisions.json',dict(path=file['path'],**evidence))
        diff += unified_diff(file['path'],file['source_context'],updated)
    save(output/'assembly.json',dict(strategy='deterministic_telemetry_precision',model_requests=0,automatic_repairs=0,
        policy='explicit telemetry float64 widening; wire type changes, coordinated rollout required'))
    return validate_output(dict(contract_version='1.0',outcome='patch',diff=diff,
        rationale='Bounded telemetry precision widening; retain units, observation names and strict speed threshold.',confidence=0,
        assumptions=['Adopted direct binding shapes only; no general receiver or data-flow proof.',
                     'Wire type changes from fixed32 to fixed64; mixed-version delivery is outside this migration.',
                     'Confidence is unestimated; zero is a placeholder. Human review required.']))
