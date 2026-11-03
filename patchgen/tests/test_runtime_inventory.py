"""Real Git trees exercise inventory completeness, path encoding and entry modes."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from patchgen.adapter import adapt, digest, scan_manifest
from patchgen.generator import ContractError
from patchgen.locator import locate
from patchgen.runtime_inventory import inventory

ROOT = Path(__file__).resolve().parents[2]


class RuntimeInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git('init', '-q')
        self.detector = json.loads((ROOT/'patchgen/fixtures/adapter/detector.json').read_text())
        schema = self.repo/self.detector['change']['schema_path']
        schema.parent.mkdir(parents=True)
        schema.write_text(self.detector['change']['old_schema'])
        self.write('runtimes/python/main.py', 'print(entity.name)\n')
        self.detector.update(old_schema_sha256=digest(self.detector['change']['old_schema']),
                             events=[dict(category='field_renamed', old_name='name', new_name='display_name', message='simulation.v1.Entity')])

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.name=Inventory test', '-c', 'user.email=inventory@example.invalid', *args],
                              cwd=self.repo, check=True, capture_output=True, text=True).stdout

    def write(self, path, content):
        file = self.repo/path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return file

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'authored inventory fixture')
        self.detector['source_revision'] = self.git('rev-parse', 'HEAD').strip()
        return self.detector['source_revision']

    def test_regular_executable_unicode_and_auxiliary_files_are_inventoried(self):
        self.write('runtimes/python/測定.py', 'print(entity.name)\n').chmod(0o755)
        self.write('runtimes/python/requirements.txt', 'protobuf==6.33.5\n')
        self.write('runtimes/typescript/package.json', '{}\n')
        self.write('runtimes/csharp/App.csproj', '<Project/>\n')
        revision = self.commit()
        record = locate(self.repo, self.detector)
        self.assertEqual(record['status'], 'complete')
        self.assertEqual(len(record['runtime_inventory']), 5)
        self.assertEqual(len(record['scanned']), 2)
        entry = next(e for e in record['runtime_inventory'] if e['path'].endswith('測定.py'))
        self.assertEqual((entry['mode'], entry['disposition']), ('100755', 'source'))
        case, provenance = adapt(self.repo, self.detector, record)
        self.assertEqual(len(case['affected_files']), 2)
        self.assertIn('exact runtime tree', provenance['scan_verification'])
        self.assertEqual(record['runtime_inventory'], inventory(self.repo, revision))

    def test_unknown_extensions_and_extensionless_files_block_completeness(self):
        for path in ('runtimes/consumer.rb', 'runtimes/consumer', 'runtimes/notes.txt', 'runtimes/consumer.tsx'):
            with self.subTest(path=path):
                self.write(path, 'entity.name\n')
        self.commit()
        record = locate(self.repo, self.detector)
        self.assertEqual(record['status'], 'partial')
        self.assertEqual(len(record['issues']), 4)
        record['status'] = 'complete'  # Forging status cannot bypass adapter inventory.
        with self.assertRaisesRegex(ContractError, 'unsupported runtime inventory'):
            adapt(self.repo, self.detector, record)

    def test_symlink_source_and_auxiliary_entries_are_never_parsed(self):
        (self.repo/'runtimes/link.py').symlink_to('python/main.py')
        (self.repo/'runtimes/requirements.txt').symlink_to('/outside/requirements.txt')
        self.commit()
        record = locate(self.repo, self.detector)
        self.assertEqual(record['status'], 'partial')
        self.assertEqual([s['path'] for s in record['scanned']], ['runtimes/python/main.py'])
        rejected = [e for e in record['runtime_inventory'] if e['disposition'] == 'unsupported_git_entry']
        self.assertEqual(len(rejected), 2)
        record['status'] = 'complete'
        with self.assertRaisesRegex(ContractError, 'unsupported runtime inventory'):
            adapt(self.repo, self.detector, record)

    def test_gitlink_blocks_completeness_without_reading_submodule_content(self):
        revision = self.commit()
        self.git('update-index', '--add', '--cacheinfo', f'160000,{revision},runtimes/submodule')
        self.git('commit', '-qm', 'gitlink fixture')
        self.detector['source_revision'] = self.git('rev-parse', 'HEAD').strip()
        record = locate(self.repo, self.detector)
        self.assertEqual(record['status'], 'partial')
        entry = next(e for e in record['runtime_inventory'] if e['path'].endswith('submodule'))
        self.assertEqual((entry['object_type'], entry['disposition']), ('commit', 'unsupported_git_entry'))

    def test_unsafe_paths_are_explicit_blockers_instead_of_quoted_git_names(self):
        self.write('runtimes/spaced name.py', 'print(entity.name)\n')
        self.write('runtimes/new\nline.py', 'print(entity.name)\n')
        self.commit()
        record = locate(self.repo, self.detector)
        self.assertEqual(record['status'], 'partial')
        self.assertEqual(len(record['issues']), 2)
        self.assertTrue(all(i['reason'] == 'unsupported_path' for i in record['issues']))
        self.assertEqual(len(record['scanned']), 1)

    def test_inventory_tampering_and_missing_rows_are_rejected(self):
        self.write('runtimes/python/requirements.txt', 'protobuf==6.33.5\n')
        revision = self.commit()
        original = locate(self.repo, self.detector)
        for mutation in ('drop_inventory', 'drop_row', 'mode', 'object_id', 'disposition'):
            record = copy.deepcopy(original)
            if mutation == 'drop_inventory': record.pop('runtime_inventory')
            elif mutation == 'drop_row': record['runtime_inventory'].pop()
            else: record['runtime_inventory'][0][mutation] = 'forged'
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ContractError, 'runtime inventory'):
                scan_manifest(self.repo, revision, record)
        legacy = copy.deepcopy(original)
        legacy['producer'] = 'independent-tree-sitter-locator/1.3'
        legacy['scan_manifest_version'] = '1.0'
        legacy.pop('runtime_inventory')
        self.assertEqual(set(scan_manifest(self.repo, revision, legacy)), {'runtimes/python/main.py'})

    def test_current_producer_cannot_drop_or_downgrade_manifest(self):
        revision = self.commit()
        original = locate(self.repo, self.detector)
        for producer in ('independent-tree-sitter-locator/1.3', 'independent-tree-sitter-locator/1.4', original['producer']):
            record = dict(original, producer=producer)
            record.pop('scan_manifest_version')
            with self.subTest(producer=producer), self.assertRaisesRegex(ContractError, 'manifest'):
                scan_manifest(self.repo, revision, record)
        for mutation in ('drop_version', 'downgrade', 'drop_all', 'drop_version_with_scan'):
            record = copy.deepcopy(original)
            if mutation == 'downgrade': record['scan_manifest_version'] = '1.0'
            else: record.pop('scan_manifest_version')
            if mutation == 'drop_all':
                record.pop('runtime_inventory')
                record.pop('scanned')
            elif mutation == 'drop_version_with_scan': record.pop('runtime_inventory')
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ContractError, 'manifest'):
                adapt(self.repo, self.detector, record)
        legacy = copy.deepcopy(original)
        legacy['producer'] = 'manually reviewed fixture; not live locator'
        for key in ('scan_manifest_version', 'runtime_inventory', 'scanned'): legacy.pop(key)
        _, provenance = adapt(self.repo, self.detector, legacy)
        self.assertEqual(provenance['scan_verification'], 'legacy supplied files only')

    def test_orphaned_manifest_fields_are_not_legacy_records(self):
        revision = self.commit()
        for record in ({'scanned': []}, {'runtime_inventory': []}):
            with self.subTest(record=record), self.assertRaisesRegex(ContractError, 'manifest'):
                scan_manifest(self.repo, revision, record)

    def test_same_generated_ts_member_rename_survives_adapter(self):
        from patchgen.detector import detect
        old = 'syntax="proto3"; package simulation.v1; message Entity { float speed_mps=1; }'
        new = old.replace('speed_mps', 'speedMps')
        path = 'proto/v1/entity.proto'
        self.write(path, old)
        self.write('runtimes/typescript/main.ts',
                   'import { Entity as V } from "../../generated/ts/v1/entity";\n'
                   'const e = V.decode(data);\nconsole.log(e.speedMps);\n')
        revision = self.commit()
        detector = detect(old, new, path, revision, 'same-ts-member', 'Preserve speed value')
        record = locate(self.repo, detector)
        case, _ = adapt(self.repo, detector, record)
        position = next(f for f in case['affected_files'] if f['language'] == 'typescript')['positions'][0]
        self.assertTrue(position['binding_evidence'])
        self.assertIs(position['required_reference'], False)
        changed = copy.deepcopy(record)
        next(f for f in changed['files'] if f['language'] == 'typescript')['positions'][0]['required_reference'] = True
        with self.assertRaisesRegex(ContractError, 'required flag'):
            adapt(self.repo, detector, changed)

    def test_advertised_live_detector_cannot_strip_or_forge_events(self):
        from patchgen.detector import detect
        change = self.detector['change']
        self.write('runtimes/python/main.py', 'from v1.entity_pb2 import Entity as V\ne = V(name="a")\nprint(e.name)\n')
        revision = self.commit()
        detector = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                          revision, change['id'], self.detector['intended_behavior'])
        record = locate(self.repo, detector)
        adapt(self.repo, detector, record)
        for mutation in ('drop_events', 'empty_events', 'old_name', 'message', 'new_schema',
                         'schema_hash', 'descriptor_hash', 'unsupported', 'structural_status'):
            changed = copy.deepcopy(detector)
            stripped = copy.deepcopy(record)
            # A stripped event plus stripped flags must not select legacy semantics.
            for file in stripped['files']:
                for position in file['positions']:
                    position.pop('binding_evidence', None)
                    position.pop('required_reference', None)
            if mutation == 'drop_events': changed.pop('events')
            elif mutation == 'empty_events': changed['events'] = []
            elif mutation in ('old_name', 'message'): changed['events'][0][mutation] = 'forged'
            elif mutation == 'new_schema': changed['change']['new_schema'] = change['old_schema']
            elif mutation == 'schema_hash': changed['new_schema_sha256'] = '0'*64
            elif mutation == 'descriptor_hash': changed['old_descriptor_sha256'] = '0'*64
            elif mutation == 'unsupported': changed['unsupported'] = ['companion metadata edit']
            else: changed['structural_status'] = 'no_structural_change'
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ContractError, 'detector'):
                adapt(self.repo, changed, stripped)

    def test_generated_csharp_members_and_custom_json_key_are_candidates(self):
        from patchgen.detector import detect
        path = 'model.proto'
        old = 'syntax="proto3"; message Packet { optional string parser=1 [json_name="wire-parser"]; }'
        new = old.replace('string parser', 'string caption')
        self.write(path, old)
        self.write('runtimes/csharp/Read.cs', """class Reader {
    void Read(Packet packet) {
        Log(packet.Parser_);
        Log(Packet.Parser_FieldNumber);
        Log(packet.HasParser_);
        packet.ClearParser_();
        Log(packet.Parser);
    }
}
""")
        self.write('runtimes/python/main.py', 'def read(payload):\n    key = "wire-parser"\n    return payload[key]\n\ndef present(message):\n    return message.WhichOneof("_parser")\n')
        revision = self.commit()
        record = locate(self.repo, detect(old, new, path, revision, 'rename', 'Preserve presence and JSON key'))
        self.assertEqual(record['status'], 'complete')
        self.assertEqual({f['language']: [p['start_line'] for p in f['positions']] for f in record['files']},
                         {'csharp': [3, 4, 5, 6, 7], 'python': [2, 3, 6]})
        self.assertTrue(all(not p.get('binding_evidence') for f in record['files'] for p in f['positions']))

    def test_current_locator_cannot_omit_or_fabricate_unbound_candidates(self):
        self.write('runtimes/csharp/Read.cs', 'class R { string Read() {\n Log(a.Name);\n return b.Name;\n} }\n')
        self.commit()
        record = locate(self.repo, self.detector)
        adapt(self.repo, self.detector, record)
        for mutation in ('drop_line', 'drop_file', 'fabricate_line', 'fabricate_reason'):
            changed = copy.deepcopy(record)
            target = next(f for f in changed['files'] if f['language'] == 'csharp')
            if mutation == 'drop_line':
                target['positions'].pop()
            elif mutation == 'drop_file':
                changed['files'].remove(target)
            elif mutation == 'fabricate_line':
                target['positions'][0].update(start_line=1, end_line=1)
            else:
                target['positions'][0]['reason'] = 'fabricated certainty'
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ContractError, 'syntax candidate'):
                adapt(self.repo, self.detector, changed)

    def test_current_locator_cannot_forge_complete_dynamic_scan(self):
        self.write('runtimes/python/main.py', 'def read(entity, key):\n    return entity[key]\n')
        self.commit()
        record = locate(self.repo, self.detector)
        self.assertEqual(record['status'], 'partial')
        record.update(status='complete', issues=[])
        with self.assertRaisesRegex(ContractError, 'syntax scan requires review'):
            adapt(self.repo, self.detector, record)
