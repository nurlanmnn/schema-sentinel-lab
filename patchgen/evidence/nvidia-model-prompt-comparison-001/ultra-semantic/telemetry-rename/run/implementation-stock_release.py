"""Policy for one pinned inventory enum addition."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = 'd4a3e66888e8e6a17a1cbc49b48234ba92e9d86e'
CHANGE_ID = 'inventory-stock-release'
EVENT = dict(category='enum_value_added', enum='simulation.inventory.StockState',
             value='STOCK_STATE_RELEASED', number=2)
POLICY = ('For positive inventory, allow UNSPECIFIED or RELEASED. QUARANTINED and unknown enum values '
          'stay blocked. Keep existing producer defaults, decimal quantity JSON, and the positive quantity requirement.')
ROLES = {
    'runtimes/python/inventory_runtime.py': (
        (5, 'import STOCK_STATE_UNSPECIFIED, StockItem',
         'import STOCK_STATE_RELEASED, STOCK_STATE_UNSPECIFIED, StockItem'),
        (12, 'entity.state == STOCK_STATE_UNSPECIFIED',
         'entity.state in (STOCK_STATE_UNSPECIFIED, STOCK_STATE_RELEASED)'),
    ),
    'runtimes/typescript/inventory.ts': (
        (11, 'entity.state === StockState.STOCK_STATE_UNSPECIFIED',
         '(entity.state === StockState.STOCK_STATE_UNSPECIFIED || entity.state === StockState.STOCK_STATE_RELEASED)'),
    ),
    'runtimes/csharp/Inventory.cs': (
        (15, 'entity.State == Simulation.Inventory.StockState.Unspecified',
         '(entity.State == Simulation.Inventory.StockState.Unspecified || entity.State == Simulation.Inventory.StockState.Released)'),
    ),
}


def verify_target(case):
    change = case['change']
    if (case['source_revision'] != REVISION or change['id'] != CHANGE_ID
            or change['schema_path'] != 'proto/inventory/item.proto' or case['intended_behavior'] != POLICY):
        raise ContractError('stock release requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('stock release requires exactly the supported enum addition')


def prepare(source, detector, locator):
    """Use the internal scan for this opt-in strategy while keeping generic enum generation blocked."""
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != ['enum candidates only; consumer behavior/exhaustiveness analysis unsupported']
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('stock release requires the expected candidate scope and no extra scan warnings')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope='pinned stock-release policy',
                                     locator_status='partial', generic_enum_generation='blocked')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('stock release requires its three pinned runtime files')
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
                raise ContractError(f'unresolved stock release role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              unchanged_candidate_lines=sorted(candidates - {line for line, _, _ in edits})))
    save(output / 'assembly.json', dict(strategy='deterministic_inventory_stock_release',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Extend the positive-stock allow-list to released inventory and preserve fail-closed routing.',
        confidence=0, assumptions=['Exact adopted source and stock policy only.',
            'Update consumers before producers emit RELEASED if consistent availability decisions are required.',
            'Confidence is unestimated. Human review required.']))
