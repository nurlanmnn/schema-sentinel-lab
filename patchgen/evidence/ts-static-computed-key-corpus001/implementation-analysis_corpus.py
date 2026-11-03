"""Measure authored source inventories against candidate and binding components."""
import argparse
import hashlib
import json
from pathlib import Path
from patchgen.detector import detect
from patchgen.locator import scan, attach_bindings
from patchgen.generator import save, command

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/'patchgen/analysis-corpus/cases.json'


def measure(expected, actual):
    expected, actual = set(expected), set(actual)
    return dict(expected=len(expected), matched=len(expected & actual),
                missed=sorted(expected-actual), extra=sorted(actual-expected),
                recall=len(expected & actual)/len(expected) if expected else None)


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    raw = CATALOG.read_bytes()
    catalog = json.loads(raw)
    save(output/'catalog.json', catalog)
    implementation = {}
    for name in ('analysis_corpus.py', 'detector.py', 'locator.py', 'python_bindings.py', 'runtime_inventory.py','source_spellings.py','typescript_bindings.py','binding_analysis.py'):
        content = (ROOT/'patchgen'/name).read_bytes()
        implementation[name] = hashlib.sha256(content).hexdigest()
        (output/('implementation-'+name)).write_bytes(content)
    revision = command(['git','rev-parse','HEAD'], ROOT).strip()
    detector = detect(catalog['old_schema'], catalog['new_schema'], 'vehicle.proto', revision,
                      'authored-binding-rename', catalog['intended_behavior'])
    save(output/'detector.json', detector)
    records = []
    for case in catalog['cases']:
        positions, warnings, error = scan(case['source'], case['language'], 'speed_mps')
        policy = catalog['binding_policy']
        ts_policy = policy.get('typescript')
        positions, limitations = attach_bindings(case['source'], case['language'], detector['events'][0],
                                                 (policy['module'], policy['symbol']), positions, error,
                                                 source_path=ts_policy['source_path'] if ts_policy else None,
                                                 typescript_policy=(ts_policy['module'], ts_policy['symbol']) if ts_policy else None)
        actual = [p['start_line'] for p in positions]
        bound = [p['start_line'] for p in positions if p.get('binding_evidence')]
        # Expectations are read only after production outputs have been obtained.
        record = dict(id=case['id'], positions=positions, warnings=warnings, parse_error=error,
                      binding_limitations=limitations, source_sha256=hashlib.sha256(case['source'].encode()).hexdigest(),
                      candidate_coverage=measure(case['affected_sites'], actual),
                      binding_coverage=measure(case['expected_bound'], bound),
                      expectation_match=(actual == case['expected_candidates'] and bound == case['expected_bound'] and not error))
        save(output/(case['id']+'.json'), record)
        records.append(record)
    summary = dict(scope=catalog['scope'], scenario_count=len(records),
                   expectation_matches=sum(r['expectation_match'] for r in records), records=records,
                   candidate_expected=sum(r['candidate_coverage']['expected'] for r in records),
                   candidate_matched=sum(r['candidate_coverage']['matched'] for r in records),
                   candidate_extras=sum(len(r['candidate_coverage']['extra']) for r in records),
                   bound_expected=sum(r['binding_coverage']['expected'] for r in records),
                   bound_matched=sum(r['binding_coverage']['matched'] for r in records),
                   bound_extras=sum(len(r['binding_coverage']['extra']) for r in records),
                   model_requests=0, validated_migrations=0, human_acceptance=False,
                   implementation_revision=revision, implementation=implementation,
                   catalog_sha256=hashlib.sha256(raw).hexdigest(),
                   limitations=['Explicit generated-module policy; no runtime import verification or arbitrary monkeypatch analysis.',
                                'Expected misses remain failures of analysis capability even when expectation_match is true.',
                                'No cross-function value propagation or C# binding proof; mutable TS/unknown sites remain candidates.'])
    save(output/'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output.resolve())
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','implementation')}, indent=2))
    return int(result['expectation_matches'] != result['scenario_count'])


if __name__ == '__main__':
    raise SystemExit(main())
