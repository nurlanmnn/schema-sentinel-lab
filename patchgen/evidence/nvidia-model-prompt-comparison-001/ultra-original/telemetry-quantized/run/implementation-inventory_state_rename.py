"""Policy for one pinned inventory enum symbol rename."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = 'd7efa49f9f95da951bc4b7bdd0ca4454f6a41afd'
CHANGE_ID = 'inventory-state-rename'
EVENT = dict(category='enum_value_renamed', enum='simulation.inventory.StockState',
             old_value='STOCK_STATE_QUARANTINED', new_value='STOCK_STATE_ON_HOLD', number=1)
POLICY = ('Rename the numeric stock state 1 from QUARANTINED to ON_HOLD. Expose ON_HOLD '
          'for opted-in symbolic observations and preserve the other labels, stock eligibility, '
          'producer defaults, and decimal quantity representation.')
ROLES = {
    'runtimes/python/inventory_runtime.py': (
        (5, 'STOCK_STATE_QUARANTINED', 'STOCK_STATE_ON_HOLD'),
        (18, "STOCK_STATE_QUARANTINED: 'QUARANTINED'", "STOCK_STATE_ON_HOLD: 'ON_HOLD'"),
    ),
    'runtimes/typescript/inventory.ts': (
        (8, 'StockState.STOCK_STATE_QUARANTINED: return "QUARANTINED"',
         'StockState.STOCK_STATE_ON_HOLD: return "ON_HOLD"'),
    ),
    'runtimes/csharp/Inventory.cs': (
        (22, 'StockState.Quarantined => "QUARANTINED"', 'StockState.OnHold => "ON_HOLD"'),
    ),
}


def verify_target(case):
    change = case['change']
    if (case['source_revision'] != REVISION or change['id'] != CHANGE_ID
            or change['category'] != EVENT['category']
            or change['schema_path'] != 'proto/inventory/item.proto' or case['intended_behavior'] != POLICY):
        raise ContractError('stock state rename requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('stock state rename requires exactly the supported nondefault enum rename')


def prepare(source, detector, locator):
    """Use the internal scan for this opt-in strategy while keeping generic enum generation blocked."""
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != ['enum candidates only; consumer behavior/exhaustiveness analysis unsupported']
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('stock state rename requires the expected candidate scope and no extra scan warnings')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope='pinned stock state rename policy',
                                     locator_status='partial', generic_enum_generation='blocked')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('stock state rename requires its three pinned runtime files')
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
                raise ContractError(f'unresolved stock state rename role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              unchanged_candidate_lines=sorted(candidates - {line for line, _, _ in edits})))
    save(output / 'assembly.json', dict(strategy='deterministic_inventory_state_rename',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Update the generated enum symbol and opted-in label while preserving stock eligibility.',
        confidence=0, assumptions=['Exact adopted source and stock policy only.',
            'Numeric wire values are stable. Applications that consume symbolic labels need the new name.',
            'Confidence is unestimated. Human review required.']))
