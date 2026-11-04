"""Policy for one pinned inventory quantity presence migration."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = 'd4a3e66888e8e6a17a1cbc49b48234ba92e9d86e'
CHANGE_ID = 'inventory-presence'
EVENT = dict(category='field_presence_added', message='simulation.inventory.StockItem',
             field_number=2, old_name='quantity', new_name='quantity')
POLICY = ('Accept null quantity as absent and preserve explicit zero on the wire. Observe absent '
          'quantity as JSON null and present quantity as a decimal string. Only positive quantity '
          'with unspecified stock state is eligible.')
ROLES = {
    'runtimes/python/inventory_runtime.py': (
        (10, "sample = StockItem(sku=request['sku'], quantity=int(request['quantity']))",
         "sample = StockItem(sku=request['sku'])\n    if request['quantity'] is not None:\n        sample.quantity = int(request['quantity'])"),
        (11, 'str(entity.quantity)', "str(entity.quantity) if entity.HasField('quantity') else None"),
        (12, 'entity.quantity > 0', "entity.HasField('quantity') and entity.quantity > 0"),
    ),
    'runtimes/typescript/inventory.ts': (
        (4, 'quantity: string', 'quantity: string | null'),
        (9, 'Number.parseInt(request.quantity, 10)', 'request.quantity === null ? undefined : Number.parseInt(request.quantity, 10)'),
        (10, 'entity.quantity.toString()', 'entity.quantity?.toString() ?? null'),
        (11, 'BigInt(entity.quantity) > 0n', 'entity.quantity !== undefined && BigInt(entity.quantity) > 0n'),
    ),
    'runtimes/csharp/Inventory.cs': (
        (13, 'Sku = request.Sku, Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture) };',
         'Sku = request.Sku };\n            if (request.Quantity is string quantity)\n                sample.Quantity = int.Parse(quantity, CultureInfo.InvariantCulture);'),
        (14, 'Dictionary<string, object>', 'Dictionary<string, object?>'),
        (14, 'entity.Quantity.ToString(CultureInfo.InvariantCulture)', 'entity.HasQuantity ? entity.Quantity.ToString(CultureInfo.InvariantCulture) : null'),
        (15, 'entity.Quantity > 0', 'entity.HasQuantity && entity.Quantity > 0'),
        (20, 'string Quantity', 'string? Quantity'),
    ),
}


def verify_target(case):
    change = case['change']
    if (case['source_revision'] != REVISION or change['id'] != CHANGE_ID
            or change['category'] != EVENT['category']
            or change['schema_path'] != 'proto/inventory/item.proto' or case['intended_behavior'] != POLICY):
        raise ContractError('quantity presence requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('quantity presence requires exactly the supported presence addition')


def prepare(source, detector, locator):
    """Use the existing syntax scan for the pinned strategy."""
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != ['presence candidates only; constructor and observation policy requires review']
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('quantity presence requires the expected candidate scope and no extra scan warnings')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope='pinned presence policy',
                                     locator_status='partial')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('quantity presence requires its three pinned runtime files')
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
                raise ContractError(f'unresolved quantity presence role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              unchanged_candidate_lines=sorted(candidates - {line for line, _, _ in edits})))
    save(output / 'assembly.json', dict(strategy='deterministic_inventory_presence',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Preserve absent and explicit zero across producer wire bytes and consumer observations.',
        confidence=0, assumptions=['Exact adopted source and stock policy only.',
            'Legacy writers omit zero and legacy readers conflate absent with zero.',
            'Confidence is unestimated. Human review required.']))
