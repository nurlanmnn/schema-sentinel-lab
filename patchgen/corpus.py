"""Evaluate authored domain scenarios at the detector/locator boundary only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from patchgen.detector import detect
from patchgen.locator import locate
from patchgen.adapter import adapt, coverage
from patchgen.generator import command, save

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'patchgen/corpus'


def seed(domain, output):
    """Reconstruct exact authored consumer files in an independent local Git seed."""
    source = output / 'source'
    source.mkdir(parents=True, exist_ok=False)
    shutil.copytree(CORPUS / domain / 'runtimes', source / 'runtimes')
    (source / 'model.proto').write_bytes((CORPUS / domain / 'old.proto').read_bytes())
    command(['git', 'init', '--quiet', '--template=', '--object-format=sha1'], source)
    command(['git', '-c', 'core.autocrlf=false', 'add', 'model.proto', 'runtimes'], source)
    tree = command(['git', 'write-tree'], source).strip()
    env = dict(os.environ, GIT_AUTHOR_NAME='Schema Sentinel fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Schema Sentinel fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
               GIT_AUTHOR_DATE='2026-11-02T00:00:00+00:00', GIT_COMMITTER_DATE='2026-11-02T00:00:00+00:00')
    revision = subprocess.check_output(['git', '-c', 'commit.gpgsign=false', 'commit-tree', tree, '-m',
                                         'Authored public ' + domain + ' boundary fixture'],
                                        cwd=source, env=env, text=True).strip()
    command(['git', 'update-ref', 'HEAD', revision], source)
    return source, revision


def run(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest_raw = (CORPUS / 'cases.json').read_bytes()
    catalog = json.loads(manifest_raw)
    save(output / 'catalog.json', catalog)
    implementation = {name: hashlib.sha256((ROOT / 'patchgen' / name).read_bytes()).hexdigest()
                      for name in ('corpus.py', 'detector.py', 'locator.py', 'python_bindings.py', 'adapter.py')}
    for name in implementation:
        shutil.copyfile(ROOT / 'patchgen' / name, output / ('implementation-' + name))
    records = []
    for case in catalog['cases']:
        directory = output / case['id']
        directory.mkdir()
        record = dict(id=case['id'], domain=case['domain'], proposal_validation='not_run',
                      human_approval_required=True, expectation_match=False)
        try:
            source, revision = seed(case['domain'], directory)
            detector = detect((source / 'model.proto').read_text(),
                              (CORPUS / case['domain'] / case['new_schema_file']).read_text(),
                              'model.proto', revision, case['id'], case['behavior'])
            save(directory / 'detector.json', detector)
            located = locate(source, detector)
            save(directory / 'locator.json', located)
            record.update(source_revision=revision, detector_status=detector['status'],
                          category=detector['change']['category'], locator_status=located['status'])
            if detector['status'] == 'complete' and located['status'] == 'complete':
                adapted, provenance = adapt(source, detector, located)
                save(directory / 'input.json', adapted)
                save(directory / 'provenance.json', provenance)
            # Consult authored expectations only AFTER production output is retained.
            truth = case['ground_truth']
            record['measurement'] = coverage(truth, located) if truth else None
            expected_locator = case.get('expected_locator_status', 'complete' if truth else 'partial')
            expectation_match = (record['detector_status'] == case['expected_status']
                and record['category'] == case['expected_category']
                and record['locator_status'] == expected_locator)
            if truth:
                measured = record['measurement']
                expected_extras = case.get('expected_extras', [])
                expectation_match &= (not measured['missed'] and measured['extra'] == expected_extras)
            record['expectation_match'] = bool(expectation_match)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            record['expectation_match'] = False
            record['error'] = str(error)
        save(directory / 'result.json', record)
        records.append(record)
    summary = dict(scope=catalog['scope'], scenario_count=len(records),
        expectation_matches=sum(bool(r['expectation_match']) for r in records),
        detector_complete=sum(r.get('detector_status') == 'complete' for r in records),
        locator_complete=sum(r.get('locator_status') == 'complete' for r in records),
        generated_validated_migrations=0, model_requests=0, human_acceptance=False,
        catalog_sha256=hashlib.sha256(manifest_raw).hexdigest(), implementation=implementation,
        implementation_revision=command(['git', 'rev-parse', 'HEAD'], ROOT).strip(), records=records,
        limitations=['Small authored consumer snippets; no generated bindings, builds or runtime migration.',
                     'Expected unsupported outcomes are visible limitations, not successful migrations.',
                     'Impact inventories are manual source inspection, not a measured human baseline.',
                     'No broad recall or twenty-case end-to-end benchmark claim.'])
    save(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.output)
    print(json.dumps({key: value for key, value in summary.items() if key not in ('records', 'implementation')}, indent=2))
    return int(summary['expectation_matches'] != summary['scenario_count'])


if __name__ == '__main__':
    raise SystemExit(main())
