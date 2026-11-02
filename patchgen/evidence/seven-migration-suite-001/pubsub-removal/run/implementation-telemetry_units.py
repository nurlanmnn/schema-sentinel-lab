"""Explicit adopted telemetry m/s -> km/h proposal. Semantics are supplied, not inferred."""
from tree_sitter import Language, Parser
from patchgen.locator import FACTORIES
from patchgen.detector import detect, descriptor
from patchgen.type_precision import inspect_shapes
from patchgen.rename_roles import inventory
from patchgen.generator import ContractError, save, unified_diff, validate_output


POLICY = 'Convert meters per second to kilometers per hour using factor 3.6'
THRESHOLD = 'strict threshold becomes >108.0'
OBSERVATION = 'Expose exact decoded float32 values as JSON numbers'


def target(case):
    change = case['change']
    result = detect(change['old_schema'],change['new_schema'],change['schema_path'],
                    case['source_revision'],change['id'],case['intended_behavior'])
    wanted=dict(category='field_renamed',message='simulation.telemetry.VehicleTelemetry',field_number=2,
                old_name='speed_mps',new_name='speed_kph')
    if result['status']!='complete' or result['events']!=[wanted]:
        raise ContractError('units policy only supports VehicleTelemetry.speed_mps -> speed_kph field 2')
    file,_=descriptor(change['new_schema'],change['schema_path'])
    field=next(f for m in file.message_type if m.name=='VehicleTelemetry' for f in m.field if f.number==2)
    if field.type!=2 or field.label!=1 or field.proto3_optional or field.HasField('oneof_index'):
        raise ContractError('units policy requires singular float32 outside oneof')
    if (POLICY not in case['intended_behavior'] or THRESHOLD not in case['intended_behavior']
            or 'Runtime observation key becomes speed_kph' not in case['intended_behavior']
            or OBSERVATION not in case['intended_behavior']):
        raise ContractError('units policy requires explicit conversion, threshold and observation decisions')


def transform(case, file):
    raw,nodes,candidates=inspect_shapes(file)
    text=lambda n:raw[n.start_byte:n.end_byte].decode()
    # Descriptor-derived name edits, preserving all other layout bytes.
    edits=[dict(start=t['start_byte'],end=t['end_byte'],before=t['text'],after=t['allowed'][0],role='field_rename')
           for t in inventory(case,file)]
    language=file['language']
    if language=='python':
        values=[n.child_by_field_name('value') for n in nodes if n.type=='keyword_argument'
                and text(n.child_by_field_name('name'))=='speed_mps']
        before="request['speed']";after="request['speed'] * 3.6"
    elif language=='typescript':
        values=[n.child_by_field_name('value') for n in nodes if n.type=='pair'
                and text(n.child_by_field_name('key'))=='speedMps']
        before='request.speed';after='request.speed * 3.6'
    else:
        values=[n for n in nodes if n.type=='cast_expression' and text(n)=='(float)request.Speed']
        before='(float)request.Speed';after='(float)(request.Speed * 3.6)'
    thresholds=[n for n in nodes if n.type in ('float','number','real_literal') and text(n)=='30.0']
    if len(values)!=1 or text(values[0])!=before or len(thresholds)!=1:
        raise ContractError('unsupported units producer or threshold syntax')
    for node,after,role in [(values[0],after,'producer_mps_to_kph'),(thresholds[0],'108.0','threshold_mps_to_kph')]:
        if node.start_point.row+1 not in candidates:
            raise ContractError('units expression outside located candidates')
        edits.append(dict(start=node.start_byte,end=node.end_byte,before=text(node),after=after,role=role))
    if language == 'csharp':
        observations=[n for n in nodes if n.type=='member_access_expression' and text(n)=='entity.SpeedMps'
                      and n.start_point.row+1 in candidates
                      and 'Dictionary<string, object>' in file['source_context'].splitlines()[n.start_point.row]]
        if len(observations)!=1:
            raise ContractError('unsupported C# units observation syntax')
        node=observations[0]
        # Promote decoded float32 exactly before JSON serialization; do not round it to display text.
        edits.append(dict(start=node.start_byte,end=node.start_byte,before='',after='(double)',role='exact_float32_json_number'))
    ordered=sorted(edits,key=lambda e:e['start'])
    if any(a['end']>b['start'] for a,b in zip(ordered,ordered[1:])):
        raise ContractError('overlapping units edits')
    for edit in reversed(ordered):
        raw=raw[:edit['start']]+edit['after'].encode()+raw[edit['end']:]
    if Parser(Language(FACTORIES[language]())).parse(raw).root_node.has_error:
        raise ContractError('units proposal source parse error')
    return raw.decode(),dict(edits=edits,candidate_lines=sorted(candidates))


def propose(case,output):
    target(case)
    if len(case['affected_files'])!=3 or {f['language'] for f in case['affected_files']}!={'python','typescript','csharp'}:
        raise ContractError('units policy requires all three adopted runtime files')
    diff=unified_diff(case['change']['schema_path'],case['change']['old_schema'],case['change']['new_schema'])
    for index,file in enumerate(case['affected_files'],1):
        updated,evidence=transform(case,file)
        directory=output/'deterministic'/f'{index:02d}';directory.mkdir(parents=True,exist_ok=False)
        save(directory/'units-decisions.json',dict(path=file['path'],**evidence))
        diff+=unified_diff(file['path'],file['source_context'],updated)
    save(output/'assembly.json',dict(strategy='deterministic_telemetry_units',model_requests=0,automatic_repairs=0,
        policy='explicit m/s -> km/h producer scale and predicate migration; semantics supplied by request, never inferred'))
    return validate_output(dict(contract_version='1.0',outcome='patch',diff=diff,
        rationale='Apply explicit adopted telemetry units policy to producers, observations and speed threshold.',confidence=0,
        assumptions=['Exact adopted direct bindings only; no general receiver/data-flow proof.',
                     'Semantic conversion is supplied explicitly; the descriptor detector only establishes a syntactic rename.',
                     'Same-wire-number unit changes require coordinated rollout; mixed units and mixed versions are outside scope.',
                     'Confidence unestimated; zero is a placeholder. Human review required.']))
