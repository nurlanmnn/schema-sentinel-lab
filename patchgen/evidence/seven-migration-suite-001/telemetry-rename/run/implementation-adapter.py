"""Versioned detector/locator boundary; never parses diagnostic prose as semantics."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from patchgen.generator import ContractError, command, require, safe_path, validate_input, verify_source, save

CATEGORIES={'field_removed','field_renamed','field_type_changed','enum_value_added'}
LANGUAGES={'.py':'python','.ts':'typescript','.cs':'csharp'}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


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
    files=[]
    for item in require(locator,'files',list,'locator'):
        path=safe_path(require(item,'path',str,'locator.file'))
        if not path.startswith('runtimes/') or LANGUAGES.get(Path(path).suffix)!=item.get('language'):
            raise ContractError('unsupported runtime path/language')
        context=command(['git','show',revision+':'+path],repo)
        if item.get('source_sha256')!=digest(context):raise ContractError('stale locator source hash: '+path)
        positions=require(item,'positions',list,path)
        ranges=[]
        for pos in positions:
            start=pos.get('start_line');end=pos.get('end_line')
            if type(start) is not int or type(end) is not int or not 1<=start<=end<=len(context.splitlines()):raise ContractError('invalid locator range')
            if any(start<=b and end>=a for a,b in ranges):raise ContractError('duplicate or overlapping locator ranges')
            if pos.get('resolution')!='resolved':raise ContractError('ambiguous locator site')
            ranges.append((start,end))
        files.append(dict(path=path,language=item['language'],source_context=context,positions=[dict(start_line=p['start_line'],end_line=p['end_line'],reason=require(p,'reason',str,path)) for p in positions]))
    case=validate_input(dict(contract_version='1.0',source_revision=revision,change=change,
        intended_behavior=require(detector,'intended_behavior',str,'detector'),affected_files=files))
    verify_source(repo,case)
    provenance=dict(adapter_version='1.0',detector_producer=detector['producer'],locator_producer=locator['producer'],
        detector_sha256=digest(json.dumps(detector,sort_keys=True)),locator_sha256=digest(json.dumps(locator,sort_keys=True)),
        source_revision=revision,integration_scope='validated supplied records; completeness asserted by producer, not proved by adapter')
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
