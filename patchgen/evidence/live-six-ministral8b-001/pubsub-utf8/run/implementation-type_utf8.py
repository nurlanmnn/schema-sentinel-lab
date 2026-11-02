"""Explicit bounded v2 string->UTF-8 bytes proposal. No model/reference response.

Recognizes the adopted testbed's version dispatch and construction syntax only.
Unknown candidate roles reject the entire proposal. This is not general data flow.
"""
import ast
import re
from tree_sitter import Language, Parser
from patchgen.locator import FACTORIES, walk
from patchgen.detector import detect, descriptor
from patchgen.generator import ContractError, save, unified_diff, validate_output


def compact(text):
    return re.sub(r'\s+', '', text)


def target(case):
    change = case['change']
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    case['source_revision'], change['id'], case['intended_behavior'])
    expected = dict(category='field_type_changed', message='simulation.v2.Entity', field_number=1,
                    old_name='entity_id', new_name='entity_id', old_type=9, new_type=12)
    if result['status'] != 'complete' or result['events'] != [expected]:
        raise ContractError('UTF-8 policy supports only singular simulation.v2.Entity.entity_id string->bytes on field 1')
    file, _ = descriptor(change['new_schema'], change['schema_path'])
    message = next(m for m in file.message_type if m.name == 'Entity')
    field = next(f for f in message.field if f.number == 1)
    if field.label != 1 or field.proto3_optional or field.HasField('oneof_index'):
        raise ContractError('UTF-8 policy requires a non-optional singular field outside oneof')


def transform(file):
    raw = file['source_context'].encode()
    tree = Parser(Language(FACTORIES[file['language']]())).parse(raw)
    if tree.root_node.has_error:
        raise ContractError('UTF-8 source parse error')
    def text(n):
        return raw[n.start_byte:n.end_byte].decode() if n else ''
    def ancestor(n, kind):
        while n and n.type != kind:
            n = n.parent
        return n
    candidates = {line for p in file['positions'] for line in range(p['start_line'],p['end_line']+1)}
    edits, decisions = [], {}
    def decision(node, role, replacement=None):
        line = node.start_point.row+1
        if line not in candidates:
            raise ContractError('recognized type site outside supplied candidate lines')
        decisions.setdefault(line, []).append(dict(role=role, changed=replacement is not None))
        if replacement is not None:
            edits.append(dict(start_byte=node.start_byte,end_byte=node.end_byte,before=text(node),after=replacement,role=role,line=line))
    language = file['language']
    if language == 'python':
        parsed = ast.parse(raw.decode())
        source = raw.decode()
        segment = lambda n: ast.get_source_segment(source,n)
        # The transformation is tied to this explicitly version-dispatched binding.
        assignments = {segment(n.targets[0]): segment(n.value) for n in ast.walk(parsed)
                       if isinstance(n,ast.Assign) and len(n.targets)==1}
        required = {
            'entity': 'importlib.import_module(f"{version}.entity_pb2").Entity.FromString(raw_bytes)',
            'module': 'importlib.import_module(f"{args.version}.entity_pb2")'}
        for name, expression in required.items():
            # entity has a separate standalone assignment, so inspect all assignments.
            if not any(isinstance(n,ast.Assign) and len(n.targets)==1 and segment(n.targets[0])==name
                       and compact(segment(n.value))==compact(expression) for n in ast.walk(parsed)):
                raise ContractError('unsupported Python version-dispatched binding: '+name)
        for n in walk(tree.root_node):
            if n.type == 'attribute' and text(n.child_by_field_name('attribute')) == 'entity_id':
                if text(n) != 'entity.entity_id' or n.parent.type != 'pair':
                    raise ContractError('unsupported Python entity_id attribute role')
                pair = n.parent
                if text(pair.child_by_field_name('key')) not in ('"entity_id"',"'entity_id'"):
                    raise ContractError('unsupported Python observation key')
                func = ancestor(n,'function_definition')
                if not func or text(func.child_by_field_name('name')) != 'process_entity':
                    raise ContractError('unsupported Python observation scope')
                decision(n,'shared_observation_v2_decode', '(entity.entity_id.decode("utf-8") if version == "v2" else entity.entity_id)')
            elif n.type == 'keyword_argument' and text(n.child_by_field_name('name')) == 'entity_id':
                call = n.parent.parent
                if text(call.child_by_field_name('function')) != 'module.Entity':
                    raise ContractError('unsupported Python constructor binding')
                value = n.child_by_field_name('value')
                if value.type != 'string':
                    raise ContractError('UTF-8 construction requires an existing text literal')
                literal = text(value)
                decision(value,'standalone_v2_encode', f'({literal}.encode("utf-8") if args.version == "v2" else {literal})')
    elif language == 'typescript':
        for version in ('v1','v2'):
            expected = f'import{{EntityasEntity{version.upper()}}}from"../../generated/ts/{version}/entity";'
            if expected not in compact(raw.decode()):
                raise ContractError('unsupported TypeScript generated import binding')
        binding = 'constentity=version==="v1"?EntityV1.decode(rawBytes):EntityV2.decode(rawBytes);'
        if binding not in compact(raw.decode()):
            raise ContractError('unsupported TypeScript version dispatch')
        for n in walk(tree.root_node):
            if n.type != 'property_identifier' or text(n) != 'entityId':
                continue
            parent = n.parent
            if parent.type == 'member_expression':
                if text(parent) != 'entity.entityId' or parent.parent.type != 'pair':
                    raise ContractError('unsupported TypeScript field access')
                func = ancestor(n,'function_declaration')
                if not func or text(func.child_by_field_name('name')) != 'processEntity':
                    raise ContractError('unsupported TypeScript observation scope')
                decision(parent,'shared_observation_v2_decode', '(version === "v2" ? new TextDecoder("utf-8", { fatal: true }).decode((entity as EntityV2).entityId) : (entity as EntityV1).entityId)')
            elif parent.type == 'pair':
                call = ancestor(parent,'call_expression')
                callee = text(call.child_by_field_name('function')) if call else ''
                if callee not in ('EntityV1.encode','EntityV2.encode'):
                    raise ContractError('unsupported TypeScript construction role')
                value = parent.child_by_field_name('value')
                if value.type != 'string':
                    raise ContractError('UTF-8 construction requires an existing text literal')
                decision(value,'v1_construction_preserved' if callee=='EntityV1.encode' else 'v2_construction_encode',
                         None if callee=='EntityV1.encode' else f'new TextEncoder().encode({text(value)})')
            else:
                raise ContractError('unsupported TypeScript entityId role')
    elif language == 'csharp':
        for n in walk(tree.root_node):
            if n.type != 'identifier' or text(n) != 'EntityId':
                continue
            parent = n.parent
            if parent.type == 'member_access_expression':
                if text(parent) != 'decoded.EntityId':
                    raise ContractError('unsupported C# entity receiver')
                block = ancestor(n,'block')
                block_text = compact(text(block))
                versions = [v for v in ('V1','V2') if f'vardecoded=Simulation.{v}.Entity.Parser.ParseFrom(rawBytes);' in block_text]
                if len(versions)!=1 or block_text.count('decoded=') != 1:
                    raise ContractError('unsupported C# decoded binding')
                decision(parent,'v1_observation_preserved' if versions==['V1'] else 'v2_observation_decode',
                         None if versions==['V1'] else 'decoded.EntityId.ToStringUtf8()')
            elif parent.type == 'assignment_expression':
                creation = ancestor(n,'object_creation_expression')
                created_type = text(creation.child_by_field_name('type')) if creation else ''
                if created_type not in ('Simulation.V1.Entity','Simulation.V2.Entity'):
                    raise ContractError('unsupported C# construction type')
                value = parent.child_by_field_name('right')
                if value.type != 'string_literal':
                    raise ContractError('UTF-8 construction requires an existing text literal')
                decision(value,'v1_construction_preserved' if created_type=='Simulation.V1.Entity' else 'v2_construction_encode',
                         None if created_type=='Simulation.V1.Entity' else f'Google.Protobuf.ByteString.CopyFromUtf8({text(value)})')
            else:
                raise ContractError('unsupported C# EntityId role')
    else:
        raise ContractError('unsupported UTF-8 language')
    if set(decisions) != candidates:
        raise ContractError('unresolved UTF-8 candidate lines: '+str(sorted(candidates-set(decisions))))
    ordered = sorted(edits,key=lambda e:e['start_byte'])
    if any(a['end_byte'] > b['start_byte'] for a,b in zip(ordered,ordered[1:])):
        raise ContractError('overlapping UTF-8 expression edits')
    for edit in reversed(ordered):
        raw = raw[:edit['start_byte']]+edit['after'].encode()+raw[edit['end_byte']:]
    if Parser(Language(FACTORIES[language]())).parse(raw).root_node.has_error:
        raise ContractError('transformed UTF-8 source parse error')
    return raw.decode(), dict(edits=edits,candidate_decisions=decisions)


def propose(case, output):
    target(case)
    diff = unified_diff(case['change']['schema_path'],case['change']['old_schema'],case['change']['new_schema'])
    for index,file in enumerate(case['affected_files'],1):
        updated, evidence = transform(file)
        directory=output/'deterministic'/f'{index:02d}'
        directory.mkdir(parents=True,exist_ok=False)
        save(directory/'expression-edits.json',dict(path=file['path'],**evidence))
        diff += unified_diff(file['path'],file['source_context'],updated)
    save(output/'assembly.json',dict(strategy='deterministic_utf8_v2',model_requests=0,automatic_repairs=0,
                                    policy='explicit v2 UTF-8 text conversion; invalid byte and mixed-version policy outside scope'))
    return validate_output(dict(contract_version='1.0',outcome='patch',diff=diff,
        rationale='Bounded syntax-based v2 UTF-8 conversion proposal; v1 sites explicitly preserved.',confidence=0,
        assumptions=['Explicit deterministic UTF-8 policy, not inferred semantics or model output.',
                     'Only adopted testbed binding/dispatch shapes supported; human review required.',
                     'Confidence unestimated; zero is a placeholder, not a probability.']))
