"""Five pinned screening cases; recipes and answers never enter model context."""
import json
from pathlib import Path

PROFILES = (
    'fresh-entity-name-presence',
    'fresh-telemetry-speed-presence',
    'fresh-telemetry-asset-rename',
    'fresh-inventory-quantity-unsigned',
    'fresh-inventory-state-bool',
)
ROOT = Path(__file__).resolve().parents[1]
STRATEGY = 'deterministic_fresh'

# Exact adopted source replacements, not a general migration engine.
EDITS = {
    PROFILES[0]: {
        'runtimes/python/main.py': [('fields["name"] = entity.name', 'fields["name"] = entity.name if entity.HasField("name") else None')],
        'runtimes/typescript/main.ts': [('{ name: (entity as EntityV1).name }', '{ name: (entity as EntityV1).name ?? null }')],
        'runtimes/csharp/main.cs': [('Dictionary<string, string>', 'Dictionary<string, string?>'), ('["name"] = decoded.Name', '["name"] = decoded.HasName ? decoded.Name : null')],
    },
    PROFILES[1]: {
        'runtimes/python/telemetry_runtime.py': [
            ("sample = VehicleTelemetry(vehicle_id=request['vehicle_id'], speed_mps=request['speed'])", "sample = VehicleTelemetry(vehicle_id=request['vehicle_id'])\n    if request.get('speed') is not None:\n        sample.speed_mps = request['speed']"),
            ("'speed_mps': entity.speed_mps", "'speed_mps': entity.speed_mps if entity.HasField('speed_mps') else None"),
            ('entity.speed_mps > 30.0', "entity.HasField('speed_mps') and entity.speed_mps > 30.0")],
        'runtimes/typescript/telemetry.ts': [
            ('speed: number', 'speed?: number | null'), ('speedMps: request.speed', 'speedMps: request.speed ?? undefined'),
            ('speed_mps: entity.speedMps', 'speed_mps: entity.speedMps ?? null'),
            ('entity.speedMps > 30.0', 'entity.speedMps !== undefined && entity.speedMps > 30.0')],
        'runtimes/csharp/Telemetry.cs': [
            ('VehicleId = request.VehicleId, SpeedMps = (float)request.Speed };', 'VehicleId = request.VehicleId };\n            if (request.Speed is double speed) sample.SpeedMps = (float)speed;'),
            ('Dictionary<string, object>', 'Dictionary<string, object?>'),
            ('["speed_mps"] = entity.SpeedMps', '["speed_mps"] = entity.HasSpeedMps ? (double)entity.SpeedMps : null'),
            ('entity.SpeedMps > 30.0', 'entity.HasSpeedMps && entity.SpeedMps > 30.0'),
            ('double Speed);', 'double? Speed = null);')],
    },
    PROFILES[2]: {
        'runtimes/python/telemetry_runtime.py': [
            ("vehicle_id=request['vehicle_id']", "asset_id=request['vehicle_id']"),
            ("'vehicle_id': entity.vehicle_id", "'asset_id': entity.asset_id")],
        'runtimes/typescript/telemetry.ts': [
            ('vehicleId: request.vehicle_id', 'assetId: request.vehicle_id'),
            ('vehicle_id: entity.vehicleId', 'asset_id: entity.assetId')],
        'runtimes/csharp/Telemetry.cs': [
            ('VehicleId = request.VehicleId', 'AssetId = request.VehicleId'),
            ('["vehicle_id"] = entity.VehicleId', '["asset_id"] = entity.AssetId')],
    },
    PROFILES[3]: {
        'runtimes/python/inventory_runtime.py': [("quantity=int(request['quantity'])", "quantity=max(0, min(4294967295, int(request['quantity'])))")],
        'runtimes/typescript/inventory.ts': [('quantity: Number.parseInt(request.quantity, 10)', 'quantity: Math.max(0, Math.min(4294967295, Number.parseInt(request.quantity, 10)))')],
        'runtimes/csharp/Inventory.cs': [('Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture)', 'Quantity = (uint)Math.Clamp(long.Parse(request.Quantity, CultureInfo.InvariantCulture), 0L, 4294967295L)')],
    },
    PROFILES[4]: {
        'runtimes/python/inventory_runtime.py': [
            ("quantity=int(request['quantity']),", "quantity=int(request['quantity']), state=request.get('quarantined', False),"),
            ("STOCK_STATE_UNSPECIFIED: 'UNSPECIFIED'", "False: 'UNSPECIFIED'"),
            ("STOCK_STATE_QUARANTINED: 'QUARANTINED'", "True: 'QUARANTINED'"),
            ('entity.state == STOCK_STATE_UNSPECIFIED', 'not entity.state')],
        'runtimes/typescript/inventory.ts': [
            ('include_state?: boolean;', 'include_state?: boolean; quarantined?: boolean;'),
            ('stateLabel(state: StockState)', 'stateLabel(state: boolean)'),
            ('case StockState.STOCK_STATE_UNSPECIFIED:', 'case false:'),
            ('case StockState.STOCK_STATE_QUARANTINED:', 'case true:'),
            ('state: StockState.STOCK_STATE_UNSPECIFIED', 'state: request.quarantined ?? false'),
            ('entity.state === StockState.STOCK_STATE_UNSPECIFIED', '!entity.state')],
        'runtimes/csharp/Inventory.cs': [
            ('Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture) };', 'Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture), State = request.Quarantined };'),
            ('StockState.Unspecified =>', 'false =>'), ('StockState.Quarantined =>', 'true =>'),
            ('                    _ => "UNKNOWN",\n', ''),
            ('entity.State == Simulation.Inventory.StockState.Unspecified', '!entity.State'),
            ('bool IncludeState = false,', 'bool IncludeState = false, bool Quarantined = false,')],
    },
}


def fixture(name, root=ROOT):
    if name not in PROFILES:
        raise ValueError('unknown fresh case')
    return json.loads((root/'patchgen/fixtures'/name/'runtime-input.json').read_text())


def verify_target(case):
    from patchgen.generator import ContractError
    expected = fixture(case['change']['id'])
    if (case['source_revision'] != expected['source_revision'] or case['intended_behavior'] != expected['intended_behavior']
            or any(case['change'][key] != value for key, value in expected['change'].items())):
        raise ContractError('fresh case source/schema/policy differs from the authored request')


def prepare(source, detector, locator):
    """Normal adapter, with an explicit bounded presence policy for these two cases only."""
    from patchgen.adapter import adapt
    from patchgen.generator import ContractError, command, validate_input
    from patchgen.locator import locate
    case = dict(contract_version='1.0', source_revision=detector['source_revision'],
                change=detector['change'], intended_behavior=detector['intended_behavior'])
    verify_target(case)
    if detector['change']['category'] != 'field_presence_added':
        generated, provenance = adapt(source, detector, locator)
        if case['change']['id'] == PROFILES[4]:
            # Changing the defaulted state also affects constructors that omit it.
            # Quantity is an existing syntax anchor in those same constructors and
            # request declarations; these case-specific anchors point at reference edit lines.
            from patchgen.locator import scan
            for file in generated['affected_files']:
                candidates, warnings, failed = scan(file['source_context'], file['language'], 'quantity')
                if warnings or failed:
                    raise ContractError('fresh state producer anchors require review')
                seen = {p['start_line'] for p in file['positions']}
                for position in candidates:
                    if position['start_line'] not in seen:
                        file['positions'].append(dict(start_line=position['start_line'], end_line=position['end_line'],
                            reason='Explicit bool state policy: inspect defaulted producer and request near quantity'))
                file['positions'].sort(key=lambda p: p['start_line'])
            provenance['policy_anchors'] = 'quantity constructors and request declarations for explicit bool state policy'
        return generated, provenance
    from patchgen.adapter import verify_detector_record
    verify_detector_record(detector)
    if (detector['status'] != 'complete' or locator != locate(source, detector)
            or locator['issues'] != ['presence candidates only; constructor and observation policy requires review']
            or {f['path'] for f in locator['files']} != EDITS[case['change']['id']].keys()):
        raise ContractError('fresh presence requires recomputed syntax scope with no additional warnings')
    case['affected_files'] = [dict(f, source_context=command(
        ['git', 'show', case['source_revision'] + ':' + f['path']], source)) for f in locator['files']]
    if case['change']['id'] == PROFILES[1]:
        from patchgen.locator import scan
        for file in case['affected_files']:
            positions, warnings, failed = scan(file['source_context'], file['language'], 'speed')
            if warnings or failed:
                raise ContractError('fresh presence producer anchors require review')
            seen = {p['start_line'] for p in file['positions']}
            file['positions'] += [dict(start_line=p['start_line'],end_line=p['end_line'],
                reason='Explicit optional speed request policy') for p in positions if p['start_line'] not in seen]
            file['positions'].sort(key=lambda p:p['start_line'])
    return validate_input(case), dict(source_revision=case['source_revision'],
        scope='explicit fresh presence policy; candidate scope recomputed; no data-flow completeness claim', locator_status='partial')


def transform(name, path, source):
    from patchgen.generator import ContractError
    for before, after in EDITS[name][path]:
        if source.count(before) < 1 or (source.count(before) != 1 and before != 'Dictionary<string, string>'):
            raise ContractError(f'unresolved fresh recipe role: {path}: {before}')
        source = source.replace(before, after)
    return source


def propose(case, output):
    from patchgen.generator import ContractError, save, unified_diff, validate_output
    verify_target(case)
    name = case['change']['id']
    if {f['path'] for f in case['affected_files']} != EDITS[name].keys():
        raise ContractError('fresh recipe requires all three runtime files')
    change = case['change']
    diff = unified_diff(change['schema_path'], change['old_schema'], change['new_schema'])
    files = {f['path']: f for f in case['affected_files']}
    for path in EDITS[name]:
        file = files[path]
        diff += unified_diff(file['path'], file['source_context'], transform(name, file['path'], file['source_context']))
    save(output/'assembly.json', dict(strategy=STRATEGY, case=name, model_requests=0, automatic_repairs=0))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
        rationale='Apply the explicit authored migration policy to the three pinned runtimes.', confidence=0,
        assumptions=['Bounded exact-source recipe; confidence unestimated. Human review required.',
                     'Coordinated schema rollout; mixed-version deployment is outside this case.']))
