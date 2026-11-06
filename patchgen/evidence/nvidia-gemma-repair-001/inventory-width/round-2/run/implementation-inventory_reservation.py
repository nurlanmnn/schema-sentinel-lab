"""Policy for one pinned inventory stock reservation migration."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = 'd4a3e66888e8e6a17a1cbc49b48234ba92e9d86e'
CHANGE_ID = 'inventory-reservation'
EVENT = dict(category='field_added', message='simulation.inventory.StockItem',
             field_number=5, old_name=None, new_name='reserved_quantity')
SCHEMA_PATH = 'proto/inventory/item.proto'
ANCHOR_FIELD = 'quantity'
POLICY = ('Add reserved quantity with an implicit zero default. Producers accept an optional '
          'int32 reserved_quantity and keep quantity as a decimal string. Stock is eligible '
          'only when state is unspecified, reserved quantity is nonnegative, and total '
          'quantity exceeds reserved quantity. Preserve the existing observation shape.')
ROLES = {
    'runtimes/python/inventory_runtime.py': (
        (10, "quantity=int(request['quantity']))",
         "quantity=int(request['quantity']),\n                       reserved_quantity=request.get('reserved_quantity', 0))"),
        (12, 'entity.quantity > 0', '0 <= entity.reserved_quantity < entity.quantity'),
    ),
    'runtimes/typescript/inventory.ts': (
        (4, 'quantity: string', 'quantity: string; reserved_quantity?: number'),
        (9, 'state: StockState.STOCK_STATE_UNSPECIFIED',
         'state: StockState.STOCK_STATE_UNSPECIFIED, reservedQuantity: request.reserved_quantity ?? 0'),
        (11, 'BigInt(entity.quantity) > 0n',
         'entity.reservedQuantity >= 0 && entity.quantity > entity.reservedQuantity'),
    ),
    'runtimes/csharp/Inventory.cs': (
        (13, 'Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture) };',
         'Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture), ReservedQuantity = request.ReservedQuantity };'),
        (15, 'entity.Quantity > 0', 'entity.ReservedQuantity >= 0 && entity.Quantity > entity.ReservedQuantity'),
        (20, 'string Quantity);',
         'string Quantity, [property: System.Text.Json.Serialization.JsonPropertyName("reserved_quantity")] int ReservedQuantity = 0);'),
    ),
}


def is_pinned_case(case):
    change = case['change']
    return (case['source_revision'] == REVISION and change['id'] == CHANGE_ID
            and change['category'] == EVENT['category'] and change['schema_path'] == SCHEMA_PATH
            and case['intended_behavior'] == POLICY)


def policy_anchor(detector):
    if is_pinned_case(detector) and matches_single_event(detector, EVENT):
        return ANCHOR_FIELD
    return None


def verify_target(case):
    if not is_pinned_case(case):
        raise ContractError('stock reservation requires its exact source, schema identity and policy')
    change = case['change']
    result = detect(change['old_schema'], change['new_schema'], SCHEMA_PATH,
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('stock reservation requires exactly the supported scalar addition')


def prepare(source, detector, locator):
    """Use the existing syntax scan for the pinned strategy."""
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != ['addition candidates only; dependent behavior requires review']
            or locator.get('added_field_policy_anchor') != ANCHOR_FIELD
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('stock reservation requires the expected candidate scope and no extra scan warnings')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope='pinned reservation policy', anchor_field=ANCHOR_FIELD,
                                     locator_status='partial')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('stock reservation requires its three pinned runtime files')
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
                raise ContractError(f'unresolved stock reservation role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              unchanged_candidate_lines=sorted(candidates - {line for line, _, _ in edits})))
    save(output / 'assembly.json', dict(strategy='deterministic_inventory_reservation',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Enforce reservation-aware eligibility while preserving decimal quantity observations.',
        confidence=0, assumptions=['Exact adopted source and stock policy only.',
            'Upgrade readers before writers send reservations to avoid overstating availability.',
            'Confidence is unestimated. Human review required.']))
