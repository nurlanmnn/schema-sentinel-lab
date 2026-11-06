"""Policies for pinned inventory packing, routing, and enum retirement."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

SCHEMA = 'proto/inventory/item.proto'
PACKING_SOURCE = 'ba9ebb103102b1c513091e083ab8149eeb4460dd'
ROUTING_SOURCE = '1b96fa988852e92bb06e4661091215b61bf31382'
ENUM_SOURCE = 'd7efa49f9f95da951bc4b7bdd0ca4454f6a41afd'
PYTHON = 'runtimes/python/inventory_runtime.py'
TYPESCRIPT = 'runtimes/typescript/inventory.ts'
CSHARP = 'runtimes/csharp/Inventory.cs'
POLICIES = {
    'packed-bins': (
        PACKING_SOURCE, dict(category='field_packing_changed', message='simulation.inventory.StockItem',
                             field_number=6, old_name='bin_counts', old_packed=False, new_packed=True),
        'Write packed bin counts and accept packed and unpacked input. Preserve order and stock eligibility.',
        'metadata candidates only; wire or JSON policy requires review',
    ),
    'routing-oneof': (
        ROUTING_SOURCE, dict(category='fields_grouped_in_oneof', message='simulation.inventory.StockItem',
                             member_names=['warehouse', 'drop_zone'], member_numbers=[7, 8], oneof='destination'),
        'Write one nonempty destination. Prefer drop_zone over warehouse when both are supplied. Read payloads with at most one destination tag.',
        'oneof candidates only; exclusivity policy requires review',
    ),
    'state-retirement': (
        ENUM_SOURCE, dict(category='enum_value_retired', enum='simulation.inventory.StockState',
                          old_value='STOCK_STATE_QUARANTINED', number=1),
        'Reserve quarantined state name and value. Report historical value 1 as UNKNOWN and keep it ineligible.',
        'enum candidates only; consumer behavior/exhaustiveness analysis unsupported',
    ),
}
ROLES = {
    'packed-bins': {PYTHON: (11, 17), TYPESCRIPT: (17, 22), CSHARP: (16, 23)},
    'routing-oneof': {PYTHON: (12, 17, 18), TYPESCRIPT: (18, 22), CSHARP: (16, 17, 22, 23)},
    'state-retirement': {PYTHON: (5, 18), TYPESCRIPT: (8,), CSHARP: (22,)},
}
EDITS = {
    'routing-oneof': {
        PYTHON: [(12, "warehouse=request.get('warehouse', ''), drop_zone=request.get('drop_zone', ''))",
                  "warehouse=None if request.get('drop_zone') else request.get('warehouse') or None,\n"
                  "                       drop_zone=request.get('drop_zone') or None)")],
        TYPESCRIPT: [(18, 'warehouse: request.warehouse ?? "", dropZone: request.drop_zone ?? ""',
                      'warehouse: request.drop_zone ? undefined : (request.warehouse || undefined),\n'
                      '      dropZone: request.drop_zone || undefined'),
                     (22, 'warehouse: entity.warehouse, drop_zone: entity.dropZone',
                      'warehouse: entity.warehouse ?? "", drop_zone: entity.dropZone ?? ""')],
        CSHARP: [(16, 'sample.Warehouse = request.Warehouse ?? "";',
                  'if (!string.IsNullOrEmpty(request.DropZone))\n'
                  '                sample.DropZone = request.DropZone;\n'
                  '            else if (!string.IsNullOrEmpty(request.Warehouse))\n'
                  '                sample.Warehouse = request.Warehouse;'),
                 (17, '            sample.DropZone = request.DropZone ?? "";\n', '')],
    },
    'state-retirement': {
        PYTHON: [(5, 'STOCK_STATE_QUARANTINED, ', ''),
                 (18, "            STOCK_STATE_QUARANTINED: 'QUARANTINED',\n", '')],
        TYPESCRIPT: [(8, '    case StockState.STOCK_STATE_QUARANTINED: return "QUARANTINED";\n', '')],
        CSHARP: [(22, '                    StockState.Quarantined => "QUARANTINED",\n', '')],
    },
}


def verify_target(case, mode):
    revision, event, behavior, _ = POLICIES[mode]
    change = case['change']
    if (case['source_revision'] != revision or change['schema_path'] != SCHEMA
            or change['id'] != 'inventory-' + mode or case['intended_behavior'] != behavior
            or change['category'] != event['category']):
        raise ContractError('inventory evolution requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], SCHEMA, revision, change['id'], behavior)
    if not matches_single_event(result, event):
        raise ContractError('inventory evolution requires exactly the supported descriptor event')


def prepare(source, detector, locator, mode):
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case, mode)
    revision, _, _, issue = POLICIES[mode]
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != [issue] or {file['path'] for file in locator['files']} != ROLES[mode].keys()):
        raise ContractError('inventory evolution requires the expected candidate scope')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', revision + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=revision, scope=mode, locator_status='partial')


def propose(case, output, mode):
    verify_target(case, mode)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES[mode].keys():
        raise ContractError('inventory evolution requires three pinned runtime files')
    change = case['change']
    diff = unified_diff(SCHEMA, change['old_schema'], change['new_schema'])
    decisions = []
    for path, roles in ROLES[mode].items():
        file = files[path]
        source = file['source_context']
        candidates = {line for pos in file['positions'] for line in range(pos['start_line'], pos['end_line'] + 1)}
        if not set(roles) <= candidates:
            raise ContractError(f'missing inventory evolution role in {path}')
        lines = source.splitlines(keepends=True)
        edits = EDITS.get(mode, {}).get(path, ())
        for line, old, new in edits:
            if lines[line - 1].count(old) != 1:
                raise ContractError(f'unresolved inventory evolution role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              candidate_lines=sorted(candidates)))
    save(output / 'assembly.json', dict(strategy='deterministic_inventory_' + mode.replace('-', '_'),
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale=case['intended_behavior'], confidence=0,
        assumptions=['Only the pinned application policy was evaluated.',
                     'Confidence is unestimated. Human review required.']))
