"""Participant export boundaries and submission scope."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from patchgen.generator import ContractError
from run_manual_baseline import FIXTURE, prepare, runtime_scope, sha256, verify_patch


class ManualBaselineTests(unittest.TestCase):
    def test_kit_contains_pinned_sources_and_no_evaluator_material(self):
        fixture = json.loads(FIXTURE.read_text())
        with TemporaryDirectory() as temporary:
            kit = Path(temporary) / 'kit'
            prepare(kit)
            archive = kit / 'source.zip'
            manifest = json.loads((kit / 'manifest.json').read_text())
            self.assertEqual(manifest['source_sha256'], sha256(archive))
            self.assertEqual(manifest['source_revision'], fixture['source_revision'])
            with ZipFile(archive) as source:
                self.assertEqual(source.read(fixture['change']['schema_path']).decode(),
                                 fixture['change']['old_schema'])
                for path in source.namelist():
                    self.assertIn(path.split('/')[0], {
                        'proto', 'runtimes', 'generated', 'buf.yaml', 'buf.gen.yaml',
                        '.gitattributes', '.gitignore',
                    })

    def test_scope_rejects_evaluator_file(self):
        case = json.loads(FIXTURE.read_text())
        allowed = runtime_scope(case)
        with TemporaryDirectory() as temporary:
            patch = Path(temporary) / 'bad.patch'
            patch.write_text('diff --git a/run_local.py b/run_local.py\n')
            with self.assertRaisesRegex(ContractError, 'path not allowed'):
                verify_patch(patch, case, allowed)
