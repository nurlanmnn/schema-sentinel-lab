"""Bounded v1 Entity.name removal for the adopted testbed syntax, without inference."""
from tree_sitter import Language, Parser
from patchgen.locator import FACTORIES, walk
from patchgen.detector import detect, descriptor, matches_single_event
from patchgen.type_utf8 import compact
from patchgen.generator import ContractError, save, unified_diff, validate_output


def target(case):
    c = case['change']
    result = detect(c['old_schema'], c['new_schema'], c['schema_path'],
                    case['source_revision'], c['id'], case['intended_behavior'])
    expected = dict(category='field_removed', message='simulation.v1.Entity', field_number=2,
                    old_name='name', new_name=None)
    if not matches_single_event(result, expected):
        raise ContractError('Removal policy supports only singular simulation.v1.Entity.name string field 2')
    old, _ = descriptor(c['old_schema'], c['schema_path'])
    new, _ = descriptor(c['new_schema'], c['schema_path'])
    field = next(f for m in old.message_type if m.name == 'Entity' for f in m.field if f.number == 2)
    message = next(m for m in new.message_type if m.name == 'Entity')
    if field.type != 9 or field.label != 1 or field.proto3_optional or field.HasField('oneof_index'):
        raise ContractError('Removal requires a non-optional singular field outside oneof')
    if 'name' not in message.reserved_name or not any(r.start <= 2 < r.end for r in message.reserved_range):
        raise ContractError('Removed field number and name must both be reserved')


def transform(file):
    raw = file['source_context'].encode()
    language = file['language']
    tree = Parser(Language(FACTORIES[language]())).parse(raw)
    if tree.root_node.has_error:
        raise ContractError('Removal source parse error')
    def text(n):
        return raw[n.start_byte:n.end_byte].decode() if n else ''
    def ancestor(n, kind):
        while n and n.type != kind:
            n = n.parent
        return n
    candidates = {i for p in file['positions'] for i in range(p['start_line'], p['end_line']+1)}
    edits = {}
    target_nodes = []
    def remove(node, role, comma=False):
        start = node.start_byte
        if comma:
            previous = node.prev_sibling
            if not previous or previous.type != ',' or raw[previous.end_byte:start].strip():
                raise ContractError('Removal supports only a trailing item preceded by a plain comma')
            # Refuse trailing siblings other than the enclosing closing delimiter.
            if node.next_sibling and node.next_sibling.type not in ('}', ')'):
                raise ContractError('Removal supports only the final initializer item')
            start = previous.start_byte
        edits[(start, node.end_byte)] = dict(start_byte=start, end_byte=node.end_byte,
            before=raw[start:node.end_byte].decode(), after='', role=role,
            start_line=node.start_point.row+1, end_line=node.end_point.row+1)

    source = compact(raw.decode())
    if language == 'python':
        for binding in ('entity=importlib.import_module(f"{version}.entity_pb2").Entity.FromString(raw_bytes)',
                        'module=importlib.import_module(f"{args.version}.entity_pb2")'):
            if binding not in source:
                raise ContractError('Unsupported Python removal binding')
        for n in walk(tree.root_node):
            if n.type != 'attribute' or text(n.child_by_field_name('attribute')) != 'name':
                continue
            target_nodes.append(n)
            statement = ancestor(n, 'expression_statement')
            guard = statement.parent.parent if statement and statement.parent.type == 'block' else None
            if (text(n) != 'entity.name' or not guard or guard.type != 'if_statement'
                    or guard.child_by_field_name('alternative')
                    or len(statement.parent.named_children) != 1):
                raise ContractError('Unsupported Python removal statement/guard')
            condition = compact(text(guard.child_by_field_name('condition')))
            body = compact(text(statement))
            if condition == 'version=="v1"' and body == 'fields["name"]=entity.name':
                role = 'v1_observation_guard'
            elif condition == 'args.version=="v1"' and body.startswith('entity.name='):
                assignment = statement.named_children[0]
                if assignment.type != 'assignment' or assignment.child_by_field_name('right').type != 'string':
                    raise ContractError('Removal construction must have a literal value without side effects')
                role = 'v1_standalone_guard'
            else:
                raise ContractError('Unsupported Python removal guard/body')
            remove(guard, role)
    elif language == 'typescript':
        if ('import{EntityasEntityV1}from"../../generated/ts/v1/entity";' not in source
                or 'constentity=version==="v1"?EntityV1.decode(rawBytes):EntityV2.decode(rawBytes);' not in source):
            raise ContractError('Unsupported TypeScript removal binding')
        for n in walk(tree.root_node):
            if n.type != 'property_identifier' or text(n) != 'name':
                continue
            target_nodes.append(n)
            pair = ancestor(n, 'pair')
            if not pair:
                raise ContractError('Unsupported TypeScript name access')
            spread = ancestor(pair, 'spread_element')
            if spread:
                declarator = ancestor(spread, 'variable_declarator')
                if (compact(text(spread)) != '...(version==="v1"?{name:(entityasEntityV1).name}:{})'
                        or not declarator or text(declarator.child_by_field_name('name')) != 'fields'):
                    raise ContractError('Unsupported TypeScript observation spread')
                remove(spread, 'v1_observation_spread', comma=True)
            else:
                call = ancestor(pair, 'call_expression')
                if (not call or text(call.child_by_field_name('function')) != 'EntityV1.encode'
                        or text(pair.child_by_field_name('key')) != 'name'
                        or pair.child_by_field_name('value').type != 'string'):
                    raise ContractError('Unsupported TypeScript constructor item')
                remove(pair, 'v1_construction_item', comma=True)
    elif language == 'csharp':
        for n in walk(tree.root_node):
            if n.type != 'identifier' or text(n) != 'Name':
                continue
            target_nodes.append(n)
            assignment = ancestor(n, 'assignment_expression')
            if not assignment:
                raise ContractError('Unsupported C# removal access')
            if n.parent.type == 'member_access_expression':
                block = ancestor(n, 'block')
                if (compact(text(assignment)) != '["name"]=decoded.Name' or not block
                        or 'vardecoded=Simulation.V1.Entity.Parser.ParseFrom(rawBytes);' not in compact(text(block))):
                    raise ContractError('Unsupported C# observation binding')
                remove(assignment, 'v1_observation_item', comma=True)
            else:
                creation = ancestor(n, 'object_creation_expression')
                if (not creation or text(creation.child_by_field_name('type')) != 'Simulation.V1.Entity'
                        or text(assignment.child_by_field_name('left')) != 'Name'
                        or assignment.child_by_field_name('right').type != 'string_literal'):
                    raise ContractError('Unsupported C# constructor item')
                remove(assignment, 'v1_construction_item', comma=True)
    else:
        raise ContractError('Unsupported removal language')
    ordered = sorted(edits.values(), key=lambda e: e['start_byte'])
    covered = {line for e in ordered for line in range(e['start_line'], e['end_line']+1)}
    if not candidates or not candidates <= covered:
        raise ContractError('Unresolved removal candidate lines')
    for n in target_nodes:
        if n.start_point.row+1 not in candidates:
            raise ContractError('Removal token outside supplied candidate lines')
    if any(a['end_byte'] > b['start_byte'] for a, b in zip(ordered, ordered[1:])):
        raise ContractError('Overlapping removal edits')
    for e in reversed(ordered):
        raw = raw[:e['start_byte']] + raw[e['end_byte']:]
    if Parser(Language(FACTORIES[language]())).parse(raw).root_node.has_error:
        raise ContractError('Transformed removal source parse error')
    return raw.decode(), ordered


def propose(case, output):
    target(case)
    c = case['change']
    diff = unified_diff(c['schema_path'], c['old_schema'], c['new_schema'])
    for index, file in enumerate(case['affected_files'], 1):
        updated, edits = transform(file)
        directory = output / 'deterministic' / f'{index:02d}'
        directory.mkdir(parents=True, exist_ok=False)
        save(directory / 'removal-edits.json', dict(path=file['path'], edits=edits))
        diff += unified_diff(file['path'], file['source_context'], updated)
    save(output / 'assembly.json', dict(strategy='deterministic_remove_name_v1', model_requests=0,
         automatic_repairs=0, policy='adopted v1 name construction and observation removal; preserve entity_id and v2'))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff, confidence=0,
        rationale='Bounded AST removal proposal with reserved wire number/name; independent validation required.',
        assumptions=['Only adopted testbed binding/guard shapes supported; no receiver/data-flow proof.',
                     'Explicit removal policy, not model output or inferred business semantics.',
                     'Confidence unestimated; zero is a placeholder. Human review required.']))
