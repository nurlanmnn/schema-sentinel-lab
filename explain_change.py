"""Show what the change detector and impact locator find, in plain text.

Runs only the two analysis stages (no patch generation, no model, no services):

    1. patchgen.detector  compares the old and new .proto schema
    2. patchgen.locator   finds runtime code lines that may need to change

Examples:
    .venv/bin/python explain_change.py
    .venv/bin/python explain_change.py --list
    .venv/bin/python explain_change.py --fixture inventory-quantity-width
    .venv/bin/python explain_change.py --old old.proto --new new.proto --schema-path proto/v1/entity.proto
"""
import argparse
import json
import subprocess
from pathlib import Path

from patchgen.detector import detect
from patchgen.locator import locate

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / 'patchgen' / 'fixtures'


def load_case(args):
    if args.old or args.new:
        if not (args.old and args.new and args.schema_path):
            raise SystemExit('--old, --new and --schema-path must be given together')
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                                  text=True, check=True).stdout.strip()
        return dict(source_revision=revision, intended_behavior=args.behavior,
                    change=dict(id='custom', schema_path=args.schema_path,
                                old_schema=Path(args.old).read_text(), new_schema=Path(args.new).read_text()))
    return json.loads((FIXTURES / args.fixture / 'runtime-input.json').read_text())


def source_line(revision, path, line):
    text = subprocess.run(['git', 'show', f'{revision}:{path}'], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout
    return text.splitlines()[line - 1].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fixture', default='telemetry-speed-rename', help='folder name under patchgen/fixtures')
    parser.add_argument('--list', action='store_true', help='list the available fixtures and exit')
    parser.add_argument('--old', help='old .proto file (custom mode)')
    parser.add_argument('--new', help='new .proto file (custom mode)')
    parser.add_argument('--schema-path', help='repo path the schema lives at, e.g. proto/v1/entity.proto')
    parser.add_argument('--behavior', default='Explain the change.', help='intended behavior text (custom mode)')
    parser.add_argument('--json', action='store_true', help='print the raw detector and locator records')
    args = parser.parse_args()

    if args.list:
        for path in sorted(FIXTURES.glob('*/runtime-input.json')):
            print(path.parent.name)
        return 0

    case = load_case(args)
    change, revision = case['change'], case['source_revision']
    detector = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                      revision, change['id'], case['intended_behavior'])
    locator = locate(ROOT, detector)
    if args.json:
        print(json.dumps(dict(detector=detector, locator=locator), indent=2))
        return 0

    print(f"Schema: {change['schema_path']}   (runtime code read at commit {revision[:10]})")
    print(f"Intended behavior: {case['intended_behavior']}\n")

    print('STEP 1 - CHANGE DETECTION')
    print(f"  status: {detector['status']}  ({detector['structural_status']})")
    print(f"  compatibility: {detector['compatibility']}")
    for event, label in zip(detector['events'], detector['event_compatibility']):
        details = {k: v for k, v in event.items() if k not in ('old_field', 'new_field')}
        print('  event:', details)
        print(f"    -> {label['label']}: {label['reason']}")
    for change in detector['comment_changes']:
        print(f"  comment changed on {change['element']} (check units/meaning):")
        print(f"    old: {change['old_comment']}")
        print(f"    new: {change['new_comment']}")
    for reason in detector['unsupported']:
        print('  unsupported:', reason)
    for issue in detector['analysis_issues']:
        print('  issue:', issue)

    print('\nSTEP 2 - IMPACT LOCATION')
    print(f"  status: {locator['status']}   files scanned: {len(locator['scanned'])}")
    for issue in locator['issues']:
        print('  issue:', issue)
    for file in locator['files']:
        print(f"\n  {file['path']}")
        for position in file['positions']:
            line = position['start_line']
            tag = ' [bound, must edit]' if position.get('required_reference') else (
                ' [bound]' if position.get('binding_evidence') else '')
            print(f"    line {line:>3}{tag}: {source_line(revision, file['path'], line)}")
            print(f"             why: {position['reason'].removeprefix('Conservative syntax candidate: ')}")
    if not locator['files']:
        print('  no candidate lines')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
