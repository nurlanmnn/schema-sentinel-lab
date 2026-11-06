"""Policy for one pinned inventory display label migration."""
from patchgen.detector import detect, matches_single_event
from patchgen.generator import ContractError, command, save, unified_diff, validate_input, validate_output

REVISION = 'b18692397beb3550917ee7e9ba3456da73bf21ef'
CHANGE_ID = 'inventory-labels'
EVENT = dict(category='field_cardinality_changed', message='simulation.inventory.StockItem',
             field_number=4, old_name='display_labels', new_name='display_labels')
POLICY = ('Collapse display labels to the last label. Keep accepting a JSON array for construction '
          'and publish at most one label, omitting the empty default. Observe a scalar label '
          'and preserve stock eligibility. A missing label list maps to an empty string.')
ROLES = {
    'runtimes/python/inventory_runtime.py': (
        (11, "display_labels=request.get('display_labels', [])",
         "display_labels=(request.get('display_labels') or [''])[-1]"),
        (14, 'list(entity.display_labels)', 'entity.display_labels'),
    ),
    'runtimes/typescript/inventory.ts': (
        (10, 'request.display_labels ?? []', 'request.display_labels?.at(-1) ?? ""'),
    ),
    'runtimes/csharp/Inventory.cs': (
        (14, 'sample.DisplayLabels.Add(request.DisplayLabels ?? Array.Empty<string>());',
         'sample.DisplayLabels = request.DisplayLabels?.LastOrDefault() ?? "";'),
        (17, 'entity.DisplayLabels.ToArray()', 'entity.DisplayLabels'),
    ),
}


def verify_target(case):
    change = case['change']
    if (case['source_revision'] != REVISION or change['id'] != CHANGE_ID
            or change['category'] != EVENT['category']
            or change['schema_path'] != 'proto/inventory/item.proto' or case['intended_behavior'] != POLICY):
        raise ContractError('display label requires its exact source, schema identity and policy')
    result = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                    REVISION, CHANGE_ID, POLICY)
    if not matches_single_event(result, EVENT):
        raise ContractError('display label requires exactly the supported repeated-to-singular string change')


def prepare(source, detector, locator):
    """Use the existing syntax scan for the pinned strategy."""
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if (detector['status'] != 'complete' or locator['status'] != 'partial'
            or locator['issues'] != ['cardinality candidates only; collection collapse policy requires review']
            or {file['path'] for file in locator['files']} != ROLES.keys()):
        raise ContractError('display label requires the expected candidate scope and no extra scan warnings')
    case['affected_files'] = [
        dict(file, source_context=command(['git', 'show', REVISION + ':' + file['path']], source))
        for file in locator['files']
    ]
    return validate_input(case), dict(source_revision=REVISION, scope='pinned last-label policy',
                                     locator_status='partial')


def propose(case, output):
    verify_target(case)
    files = {file['path']: file for file in case['affected_files']}
    if files.keys() != ROLES.keys():
        raise ContractError('display label requires its three pinned runtime files')
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
                raise ContractError(f'unresolved display label role at {path}:{line}')
            lines[line - 1] = lines[line - 1].replace(old, new)
        diff += unified_diff(path, source, ''.join(lines))
        decisions.append(dict(path=path, edited_lines=[line for line, _, _ in edits],
                              unchanged_candidate_lines=sorted(candidates - {line for line, _, _ in edits})))
    save(output / 'assembly.json', dict(strategy='deterministic_inventory_labels',
                                       model_requests=0, decisions=decisions))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Emit and observe the last display label while preserving stock eligibility.',
        confidence=0, assumptions=['Exact adopted source and stock policy only.',
            'Legacy readers still observe a list, and new readers discard earlier occurrences.',
            'Confidence is unestimated. Human review required.']))
