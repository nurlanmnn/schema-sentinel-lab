"""Measure the pinned prototype without changing it; not a production locator."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
from patchgen.generator import command,save
from patchgen.adapter import adapt,digest

PROTOTYPE='c82fee7630b982e4da2ceda9f7fb6804fb01221c'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    code=command(['git','show',PROTOTYPE+':impact_locator.py'],Path.cwd());path=output/'locator-source.py';path.write_text(code)
    spec=importlib.util.spec_from_file_location('prototype',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    case=json.loads(Path('patchgen/fixtures/entity-name-removal/runtime-input.json').read_text())
    raw=subprocess.run(['buf','breaking','v2.bin','--against','v1.bin','--error-format','json'],cwd=args.source,text=True,capture_output=True)
    save(output/'buf-legacy.json',dict(exit=raw.returncode,stdout=raw.stdout,stderr=raw.stderr))
    records=[json.loads(line) for line in raw.stdout.splitlines() if line.strip()]
    parsed=module.extract_impacted_fields(records);save(output/'parsed-fields.json',parsed)
    sites=[];errors=[];text=io.StringIO()
    for file in case['affected_files']:
        field='Name' if file['language']=='csharp' else 'name'
        try:
            with contextlib.redirect_stdout(text):module.analyze_file_with_treesitter(str(args.source/file['path']),file['language'],field)
        except Exception as error:errors.append(dict(path=file['path'],error=repr(error)))
    (output/'tree-sitter-output.txt').write_text(text.getvalue())
    for line in text.getvalue().splitlines():
        match=re.search(r'Impact Match\] (.+):(\d+):(\d+) ->',line)
        if match:sites.append((str(Path(match[1]).relative_to(args.source)),int(match[2])))
    reference=json.loads(Path('patchgen/reference/entity-name-removal/expected.json').read_text())
    expected={(f['path'],p['start_line']) for f in reference['runtime_sites'] for p in f['positions']}
    actual=set(sites);hits=actual & expected
    save(output/'report.json',dict(prototype_revision=PROTOTYPE,source_revision=case['source_revision'],prototype_sha256=hashlib.sha256(code.encode()).hexdigest(),mode='real prototype Tree-sitter function; field supplied independently; not end-to-end integration',detector_parsed_fields=parsed,detector_descriptor_provenance='legacy committed bins refer to model.proto, not current entity.proto; stale input cannot be trusted for integration',expected_sites=len(expected),true_positive_sites=len(hits),recall=len(hits)/len(expected),missing_sites=[dict(path=p,line=l) for p,l in sorted(expected-actual)],extra_sites=[dict(path=p,line=l) for p,l in sorted(actual-expected)],errors=errors,semgrep='not run: executable unavailable',human_approval_required=True))
    locator=dict(adapter_version='1.0',producer='pinned prototype Tree-sitter measurement',status='partial',source_revision=case['source_revision'],change_id=case['change']['id'],old_schema_sha256=digest(case['change']['old_schema']),files=[])
    for file in case['affected_files']:
        positions=[dict(start_line=line,end_line=line,reason='prototype member access',resolution='resolved') for path,line in sorted(actual) if path==file['path']]
        locator['files'].append(dict(path=file['path'],language=file['language'],source_sha256=digest(file['source_context']),positions=positions))
    save(output/'locator-record.json',locator)
    detector=dict(adapter_version='1.0',producer='independent removal fixture; not live detector',status='complete',source_revision=case['source_revision'],change=case['change'],intended_behavior=case['intended_behavior'])
    try:adapt(args.source.resolve(),detector,locator)
    except ValueError as error:save(output/'adapter-rejection.json',dict(status='rejected',reason=str(error)))
    for version in ('v1','v2'):
        command(['buf','build','--path','proto/'+version,'--as-file-descriptor-set','-o',str(output/('regenerated-'+version+'.bin'))],args.source)
    fresh=subprocess.run(['buf','breaking',str(output/'regenerated-v2.bin'),'--against',str(output/'regenerated-v1.bin'),'--error-format','json'],text=True,capture_output=True)
    save(output/'buf-regenerated.json',dict(exit=fresh.returncode,stdout=fresh.stdout,stderr=fresh.stderr))
    save(output/'regenerated-parser-result.json',dict(fields=module.extract_impacted_fields([json.loads(line) for line in fresh.stdout.splitlines() if line.strip()]),scope='fresh descriptors; package/path change prevents the prototype from yielding the expected field record'))
    print((output/'report.json').read_text())


if __name__=='__main__':main()
