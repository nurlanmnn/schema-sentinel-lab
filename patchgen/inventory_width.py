"""Bounded inventory integer migrations with decimal-string JSON."""
from tree_sitter import Language, Parser
from patchgen.locator import FACTORIES, walk
from patchgen.detector import detect, descriptor, matches_single_event
from patchgen.type_utf8 import compact
from patchgen.generator import ContractError, save, unified_diff, validate_output

POLICY = 'Preserve exact signed int64 quantities as canonical decimal strings in JSON; ts-proto forceLong=string; preserve strict >0 stock predicate'
ZIGZAG_POLICY = 'Preserve signed int32 quantities, decimal-string JSON and strict >0 stock predicate with ZigZag wire encoding'
MIGRATIONS = {'width': (3, POLICY), 'zigzag': (17, ZIGZAG_POLICY)}

SHAPES = {
    'python': ["sample = StockItem(sku=request['sku'], quantity=int(request['quantity']))",
               "fields = {'sku': entity.sku, 'quantity': str(entity.quantity)}",
               "return {'fields': fields, 'in_stock': entity.quantity > 0,"],
    'typescript': ['const sample = StockItem.encode({ sku: request.sku, quantity: Number.parseInt(request.quantity, 10) }).finish();',
                   'const fields = { sku: entity.sku, quantity: entity.quantity.toString() };',
                   'return { fields, in_stock: BigInt(entity.quantity) > 0n, constructed_payload: Buffer.from(sample).toString("base64") };'],
    'csharp': ['var sample = new Simulation.Inventory.StockItem { Sku = request.Sku, Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture) };',
               'var fields = new Dictionary<string, object> { ["sku"] = entity.Sku, ["quantity"] = entity.Quantity.ToString(CultureInfo.InvariantCulture) };',
               'return new { fields, in_stock = entity.Quantity > 0, constructed_payload = Convert.ToBase64String(sample.ToByteArray()) };'],
}
BINDINGS = {
    'python': [('import_from_statement','from inventory.item_pb2 import StockItem'),
               ('assignment',"entity = StockItem.FromString(base64.b64decode(request['payload'], validate=True))")],
    'typescript': [('import_statement','import { StockItem } from "../../generated/ts/inventory/item";'),
                   ('lexical_declaration','const entity = StockItem.decode(new Uint8Array(Buffer.from(request.payload, "base64")));'),
                   ('interface_declaration','interface Request { payload: string; sku: string; quantity: string }')],
    'csharp': [('local_declaration_statement','var entity = Simulation.Inventory.StockItem.Parser.ParseFrom(Convert.FromBase64String(request.Payload));'),
               ('record_declaration','record InventoryRequest(string Payload, string Sku, string Quantity);')],
}


def target(case, migration='width'):
    if migration not in MIGRATIONS:
        raise ContractError('unsupported inventory integer migration')
    new_type, policy = MIGRATIONS[migration]
    c = case['change']
    result = detect(c['old_schema'], c['new_schema'], c['schema_path'], case['source_revision'], c['id'], case['intended_behavior'])
    event = dict(category='field_type_changed', message='simulation.inventory.StockItem', field_number=2,
                 old_name='quantity', new_name='quantity', old_type=5, new_type=new_type)
    if not matches_single_event(result, event):
        raise ContractError(f'inventory {migration} requires the declared StockItem.quantity type change at field 2')
    file, _ = descriptor(c['new_schema'], c['schema_path'])
    field = next(f for m in file.message_type if m.name == 'StockItem' for f in m.field if f.number == 2)
    if field.label != 1 or field.proto3_optional or field.HasField('oneof_index') or policy not in case['intended_behavior']:
        raise ContractError('inventory migration requires explicit policy and a nonoptional singular field')


def transform(file, migration='width'):
    language = file['language']
    if language not in SHAPES:
        raise ContractError('unsupported inventory language')
    raw = file['source_context'].encode()
    tree = Parser(Language(FACTORIES[language]())).parse(raw)
    if tree.root_node.has_error:
        raise ContractError('inventory source parse error')
    nodes = list(walk(tree.root_node))
    text = lambda n: raw[n.start_byte:n.end_byte].decode()
    for kind, wanted in BINDINGS[language]:
        if len([n for n in nodes if n.type == kind and compact(text(n)) == compact(wanted)]) != 1:
            raise ContractError('unsupported inventory generated binding or JSON input representation')
    # A quantity request declaration is a conservative syntax candidate, but needs no edit.
    lines = raw.decode().splitlines()
    candidates = {line for p in file['positions'] for line in range(p['start_line'], p['end_line'] + 1)}
    wanted = {compact(s) for s in SHAPES[language]}
    optional = {compact(s) for kind, s in BINDINGS[language] if kind in ('interface_declaration', 'record_declaration')}
    observed = {compact(lines[n - 1]) for n in candidates}
    if not wanted <= observed or not observed <= wanted | optional:
        raise ContractError('unresolved inventory candidate roles')
    for expected in SHAPES[language]:
        if not any(n.type in ('assignment', 'return_statement', 'lexical_declaration', 'local_declaration_statement')
                   and n.start_point.row + 1 in candidates and compact(lines[n.start_point.row]) == compact(expected) for n in nodes):
            raise ContractError('inventory candidates must be executable syntax')
    if migration == 'zigzag':
        return raw.decode(), dict(candidate_lines=sorted(candidates), edits=[],
                                  reason='Generated signed int32 API stays unchanged')
    before, after = {'python': ('', ''),
                     'typescript': ('Number.parseInt(request.quantity, 10)', 'request.quantity'),
                     'csharp': ('int.Parse(request.Quantity, CultureInfo.InvariantCulture)', 'long.Parse(request.Quantity, CultureInfo.InvariantCulture)')}[language]
    edits = []
    if before:
        matches = [n for n in nodes if n.type in ('call_expression', 'invocation_expression') and text(n) == before
                   and n.start_point.row + 1 in candidates]
        if len(matches) != 1:
            raise ContractError('unresolved inventory producer conversion')
        node = matches[0]
        edits.append(dict(start_byte=node.start_byte, end_byte=node.end_byte, before=before, after=after))
        raw = raw[:node.start_byte] + after.encode() + raw[node.end_byte:]
    return raw.decode(), dict(candidate_lines=sorted(candidates), edits=edits)


def propose(case, output, migration='width'):
    target(case, migration)
    if len(case['affected_files']) != 3 or {f['language'] for f in case['affected_files']} != set(SHAPES):
        raise ContractError('inventory migration requires exactly three adopted runtime files')
    diff = unified_diff(case['change']['schema_path'], case['change']['old_schema'], case['change']['new_schema'])
    for index, file in enumerate(case['affected_files'], 1):
        updated, evidence = transform(file, migration)
        directory = output / 'deterministic' / f'{index:02d}'
        directory.mkdir(parents=True, exist_ok=False)
        save(directory / 'integer-decisions.json', dict(path=file['path'], **evidence))
        diff += unified_diff(file['path'], file['source_context'], updated)
    save(output / 'assembly.json', dict(strategy=f'deterministic_inventory_{migration}', model_requests=0,
                                       automatic_repairs=0, policy=MIGRATIONS[migration][1]))
    if migration == 'zigzag':
        return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
            rationale='Use regenerated ZigZag codecs with the same signed int32 runtime API and stock predicate.',
            confidence=0, assumptions=['Adopted direct binding shapes and canonical signed int32 input strings.',
            'Old int32 bytes and new sint32 bytes are not interchangeable. Coordinate deployment and re-encode persisted payloads.',
            'Confidence is unestimated; zero is a placeholder. Human review required.']))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Preserve exact signed quantities using generated decimal-string TS values and C# long parsing; Python int already exact.',
        confidence=0, assumptions=['Adopted direct binding shapes; no general receiver/alias/dataflow proof.',
        'Valid canonical decimal inputs only. Consumers must migrate before producers emit out-of-int32 values.',
        'Confidence is unestimated; zero is a placeholder. Human review required.']))
