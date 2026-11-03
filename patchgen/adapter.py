"""Versioned detector/locator boundary; never parses diagnostic prose as semantics."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from patchgen.binding_analysis import analyze_bindings
from patchgen.runtime_inventory import LANGUAGES, inventory, blocking_entries
from patchgen.generator import ContractError, command, require, safe_path, validate_input, verify_source, save

CATEGORIES={'field_removed','field_renamed','field_type_changed','enum_value_added'}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def scan_manifest(repo, revision, locator):
    """Check an explicit scan inventory against the exact supported runtime tree."""
    if 'scan_manifest_version' not in locator:
        return None
    if locator['scan_manifest_version'] not in ('1.0', '1.1'):
        raise ContractError('unsupported scan manifest version')
    entries = inventory(repo, revision)
    if blocking_entries(entries):
        raise ContractError('scan manifest contains unsupported runtime inventory entries')
    if locator['scan_manifest_version'] == '1.1' and locator.get('runtime_inventory') != entries:
        raise ContractError('runtime inventory does not match pinned Git tree')
    expected = {entry['path'] for entry in entries if entry['disposition'] == 'source'}
    entries = require(locator, 'scanned', list, 'locator')
    contexts = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ContractError('invalid scan manifest entry')
        path = safe_path(require(entry, 'path', str, 'scan manifest'))
        if path not in expected or path in contexts or entry.get('language') != LANGUAGES[Path(path).suffix]:
            raise ContractError('scan manifest path/language mismatch')
        context = command(['git','show',revision+':'+path], repo)
        if entry.get('source_sha256') != digest(context):
            raise ContractError('stale scan manifest source hash')
        contexts[path] = context
    if set(contexts) != expected:
        raise ContractError('incomplete scan manifest')
    return contexts


def adapt(repo, detector, locator):
    for name,record in [('detector',detector),('locator',locator)]:
        if require(record,'adapter_version',str,name)!='1.0':raise ContractError('unsupported '+name+' adapter_version')
        require(record,'producer',str,name)
        if record.get('status')!='complete':raise ContractError(name+': incomplete or ambiguous input; review required')
    revision=require(detector,'source_revision',str,'detector')
    if not re.fullmatch(r'[0-9a-f]{40}',revision):raise ContractError('source_revision must be exact commit')
    change=require(detector,'change',dict,'detector')
    for key in ('id','category','old_schema','new_schema','schema_path'):require(change,key,str,'change')
    safe_path(change['schema_path'])
    if change.get('category') not in CATEGORIES:raise ContractError('unknown or ambiguous change category')
    if (locator.get('source_revision')!=revision or locator.get('change_id')!=change.get('id')
            or locator.get('old_schema_sha256')!=digest(change.get('old_schema',''))):
        raise ContractError('locator revision/change/schema identity mismatch')
    contexts = scan_manifest(repo, revision, locator)
    events = detector.get('events', [])
    if not isinstance(events, list) or events and (len(events) != 1 or not isinstance(events[0], dict) or events[0].get('category') != change['category']):
        raise ContractError('invalid or inconsistent detector events')
    files=[]
    for item in require(locator,'files',list,'locator'):
        path=safe_path(require(item,'path',str,'locator.file'))
        if not path.startswith('runtimes/') or LANGUAGES.get(Path(path).suffix)!=item.get('language'):
            raise ContractError('unsupported runtime path/language')
        if contexts is not None and path not in contexts:
            raise ContractError('locator file missing from scan manifest')
        context=contexts[path] if contexts is not None else command(['git','show',revision+':'+path],repo)
        if item.get('source_sha256')!=digest(context):raise ContractError('stale locator source hash: '+path)
        positions=require(item,'positions',list,path)
        ranges=[]
        for pos in positions:
            start=pos.get('start_line');end=pos.get('end_line')
            if type(start) is not int or type(end) is not int or not 1<=start<=end<=len(context.splitlines()):raise ContractError('invalid locator range')
            if any(start<=b and end>=a for a,b in ranges):raise ContractError('duplicate or overlapping locator ranges')
            if pos.get('resolution') not in ('candidate', 'resolved'):raise ContractError('ambiguous locator site')
            ranges.append((start,end))
        output_positions = []
        events = detector.get('events', [])
        binding_event = events[0] if len(events) == 1 and isinstance(events[0], dict) else None
        try:
            bound, _ = analyze_bindings(context, item['language'], binding_event, change['schema_path'], path)
        except SyntaxError as error:
            raise ContractError('binding source cannot be parsed') from error
        required_event = binding_event and binding_event['category'] in ('field_renamed', 'field_removed')
        if required_event and any(not any(a <= ref['line'] <= b for a, b in ranges) for ref in bound):
            raise ContractError('missing required bound reference positions')
        for pos in positions:
            result = dict(start_line=pos['start_line'], end_line=pos['end_line'], reason=require(pos,'reason',str,path))
            expected = [ref for ref in bound if pos['start_line'] <= ref['line'] <= pos['end_line']]
            if expected or 'required_reference' in pos or 'binding_evidence' in pos:
                if binding_event is None:
                    raise ContractError('binding evidence requires a supported detector event')
                if type(pos.get('required_reference')) is not bool or not isinstance(pos.get('binding_evidence'), list) or not pos['binding_evidence']:
                    raise ContractError('required-reference flag needs binding evidence')
                required = binding_event['category'] in ('field_renamed', 'field_removed')
                if (pos['required_reference'] is not required or
                        json.dumps(pos['binding_evidence'], sort_keys=True) != json.dumps(expected, sort_keys=True)):
                    raise ContractError('binding evidence/required flag does not match pinned source analysis')
                result.update(required_reference=required, binding_evidence=expected)
            output_positions.append(result)
        files.append(dict(path=path,language=item['language'],source_context=context,positions=output_positions))
    if contexts is not None and events:
        event = events[0]
        if event.get('old_name') and event['category'] in ('field_renamed', 'field_removed'):
            included = {file['path'] for file in files}
            for path, context in contexts.items():
                if path in included:
                    continue
                try:
                    bound, _ = analyze_bindings(context, LANGUAGES[Path(path).suffix], event, change['schema_path'], path)
                except SyntaxError as error:
                    raise ContractError('omitted binding source cannot be parsed') from error
                if bound:
                    raise ContractError('locator omitted a file with required bound references')
    case=validate_input(dict(contract_version='1.0',source_revision=revision,change=change,
        intended_behavior=require(detector,'intended_behavior',str,'detector'),affected_files=files))
    verify_source(repo,case)
    provenance=dict(adapter_version='1.0',detector_producer=detector['producer'],locator_producer=locator['producer'],
        detector_sha256=digest(json.dumps(detector,sort_keys=True)),locator_sha256=digest(json.dumps(locator,sort_keys=True)),
        scan_verification=('exact runtime tree inventory and supported source manifest' if locator.get('scan_manifest_version') == '1.1' else 'exact supported tracked-runtime manifest') if contexts is not None else 'legacy supplied files only',
        binding_verification='positive claims recomputed under declared repository Python/ts-proto policies; not independent analysis',
        source_revision=revision, site_resolution='candidate; optional bounded binding evidence', integration_scope='validated supplied records; completeness asserted by producer, not proved by adapter')
    return case,provenance


def coverage(reference, locator):
    expected={(f['path'],line) for f in reference['runtime_sites'] for line in f['lines']}
    actual={(f['path'],line) for f in locator['files'] for p in f['positions'] for line in range(p['start_line'],p['end_line']+1)}
    hits=expected & actual
    return dict(expected_sites=len(expected),matched_sites=len(hits),recall=len(hits)/len(expected) if expected else None,
        missed=[dict(path=p,line=l) for p,l in sorted(expected-actual)],extra=[dict(path=p,line=l) for p,l in sorted(actual-expected)])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--detector',type=Path,required=True);parser.add_argument('--locator',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    try:
        case,provenance=adapt(args.source.resolve(),json.loads(args.detector.read_text()),json.loads(args.locator.read_text()))
        save(args.output/'input.json',case);save(args.output/'provenance.json',provenance)
    except (ValueError,OSError,KeyError) as error:
        save(args.output/'error.json',dict(status='rejected',error=str(error)));raise SystemExit(str(error))


if __name__=='__main__':main()
