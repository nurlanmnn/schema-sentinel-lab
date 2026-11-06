"""Held-out registries must be complete, tamper-evident, pushed, and scored once."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from patchgen import held_out, live_suite, repair_suite
from patchgen.held_out import begin_one_shot, begin_repair, check_draft, finish, seal, verify
from patchgen.live_suite import LOCKED_CONFIG, held_out_cohorts, held_out_entries

PROFILE = 'heading-frame'
CONTROLS = ['patchgen/reference/heading-frame/wrong-axis.patch', 'patchgen/reference/heading-frame/wrong-direction.patch',
            'patchgen/reference/heading-frame/wrong-wrap.patch']
EVIDENCE = ['held-out/evidence/wrong-axis.json', 'held-out/evidence/wrong-direction.json', 'held-out/evidence/wrong-wrap.json']


def case(**changes):
    return {**dict(id='H4', case='telemetry-heading-frame', label='new_mechanism', status='sealed', profile=PROFILE,
                   approved_by='Teammate', approved_on='2026-11-06', negative_controls=list(CONTROLS),
                   control_evidence=list(EVIDENCE), reference_evidence='held-out/evidence/reference.json'), **changes}


def draft(*cases):
    return dict(evaluator=dict(name='Teammate', role='independent evaluator'), cases=list(cases) or [case()])


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)


def make_root(root):
    write(root/f'patchgen/fixtures/{PROFILE}/runtime-input.json', json.dumps(dict(source_revision='a'*40)))
    write(root/f'patchgen/reference/{PROFILE}/expected.json', '{}')
    write(root/'patchgen/held_out.py', 'harness')
    for name in CONTROLS:write(root/name, name)
    for name in EVIDENCE:write(root/name, json.dumps(dict(status='rejected')))
    write(root/'held-out/evidence/reference.json', json.dumps(dict(status='validation_passed')))
    write(root/'draft.json', json.dumps(draft()))


def sealed_root(tmp):
    root = Path(tmp); make_root(root)
    seal(root/'draft.json', root/'held-out/registry.json', root)
    return root, root/'held-out/registry.json'


class DraftTests(unittest.TestCase):
    def test_cases_need_evaluator_distinct_controls_evidence_and_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); make_root(root)
            check_draft(draft(), root)
            bad = [dict(evaluator={}, cases=[case()]), draft(case(label='easy')), draft(case(status='draft')),
                   draft(case(approved_by='')), draft(case(status='withdrawn')),
                   draft(case(negative_controls=[CONTROLS[0]] * 3)),  # one control repeated three times
                   draft(case(control_evidence=EVIDENCE[:2])), draft(case(reference_evidence=None))]
            for value in bad:
                with self.assertRaises(ValueError):check_draft(value, root)
            check_draft(draft(case(status='withdrawn', withdrawn_reason='oracle could not tell rounding modes apart')), root)
            with self.assertRaises(ValueError):check_draft(draft(case(), case()), root)

    def test_evidence_must_show_the_reference_passes_and_controls_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); make_root(root)
            write(root/EVIDENCE[1], json.dumps(dict(status='validation_passed')))  # a wrong patch that passed
            with self.assertRaisesRegex(ValueError, 'rejection'):check_draft(draft(), root)
            make_root(root); write(root/'held-out/evidence/reference.json', json.dumps(dict(status='failed')))
            with self.assertRaisesRegex(ValueError, 'reference'):check_draft(draft(), root)

    def test_variants_need_a_distinct_sealed_non_variant_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); make_root(root)
            variant = lambda **c: case(id='H4m', case='heading-minimal', **c)
            check_draft(draft(case(), variant(variant_of='H4')), root)
            for value in (draft(case(variant_of='H4')), draft(case(), variant(variant_of='H9')),
                          draft(case(variant_of='H4m'), variant(variant_of='H4')),
                          draft(case(status='withdrawn', withdrawn_reason='x'), variant(variant_of='H4'))):
                with self.assertRaises(ValueError):check_draft(value, root)


class SealTests(unittest.TestCase):
    def test_seal_covers_whole_reference_folder_and_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry = sealed_root(tmp)
            files = json.loads(registry.read_text())['cases'][0]['files']
            self.assertIn(f'patchgen/reference/{PROFILE}/expected.json', files)  # not listed in the draft
            verify(registry, root, require_git=False)
            for change in (lambda: write(root/f'patchgen/reference/{PROFILE}/hint.json', '{}'),  # new file in sealed folder
                           lambda: write(root/CONTROLS[1], 'weakened control'),
                           lambda: write(root/'patchgen/adapter.py', 'new harness code')):
                change()
                with self.assertRaisesRegex(ValueError, 'changed'):verify(registry, root, require_git=False)
                root, registry = sealed_root(tempfile.mkdtemp(dir=tmp))
            with self.assertRaises(ValueError):seal(root/'draft.json', registry, root)

    def test_evidence_content_is_rechecked_at_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry = sealed_root(tmp)
            sealed = json.loads(registry.read_text())
            # Even with a matching hash, a registry cannot point at evidence that no longer shows a rejection.
            sealed['cases'][0]['files'][EVIDENCE[0]] = held_out.digest(root/EVIDENCE[0])
            write(root/EVIDENCE[0], json.dumps(dict(status='validation_passed')))
            sealed['cases'][0]['files'][EVIDENCE[0]] = held_out.digest(root/EVIDENCE[0])
            registry.write_text(json.dumps(sealed))
            with self.assertRaisesRegex(ValueError, 'rejection'):verify(registry, root, require_git=False)

    def test_symlinks_and_outside_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'repo'; make_root(root)
            (root/CONTROLS[0]).unlink(); (root/CONTROLS[0]).symlink_to(root/CONTROLS[1])
            with self.assertRaisesRegex(ValueError, 'regular file'):seal(root/'draft.json', root/'held-out/registry.json', root)


class GitTests(unittest.TestCase):
    def repo(self, tmp):
        remote, root = Path(tmp)/'remote.git', Path(tmp)/'repo'
        self.run_git = lambda *args, cwd=root: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args],
                                                              cwd=cwd, check=True, capture_output=True)
        self.run_git('init', '--bare', str(remote), cwd=tmp); self.run_git('init', '-b', 'main', str(root), cwd=tmp)
        make_root(root); self.run_git('add', '.'); self.run_git('commit', '-m', 'base')
        write(root/'patchgen/fixtures'/PROFILE/'runtime-input.json', json.dumps(dict(
            source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip())))
        seal(root/'draft.json', root/'held-out/registry.json', root)
        self.run_git('add', '.'); self.run_git('commit', '-m', 'seal')
        self.run_git('remote', 'add', 'origin', str(remote))
        return root, root/'held-out/registry.json', (str(remote),)

    def test_seal_must_be_pushed_to_a_trusted_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry, local = self.repo(tmp)
            with self.assertRaisesRegex(ValueError, 'GitHub'):verify(registry, root, trusted_remotes=local)
            self.run_git('push', '-u', 'origin', 'main')
            with self.assertRaisesRegex(ValueError, 'GitHub'):verify(registry, root)  # local bare remote is not trusted
            verify(registry, root, trusted_remotes=local)

    def test_registry_cannot_be_replaced_or_ledger_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry, local = self.repo(tmp)
            self.run_git('push', '-u', 'origin', 'main')
            ledger = registry.parent/'attempts.jsonl'
            ledger.write_text('{"kind": "one_shot"}\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted'):verify(registry, root, trusted_remotes=local)
            self.run_git('commit', '-am', 'attempt'); ledger.write_text(''); self.run_git('commit', '-am', 'erase')
            with self.assertRaisesRegex(ValueError, 'rewritten'):verify(registry, root, trusted_remotes=local)
            self.run_git('revert', '--no-edit', 'HEAD')
            registry.write_text(registry.read_text().replace('Teammate', 'Someone')); self.run_git('commit', '-am', 'replace')
            with self.assertRaisesRegex(ValueError, 'exactly once'):verify(registry, root, trusted_remotes=local)


class LedgerTests(unittest.TestCase):
    def test_second_one_shot_needs_a_reason_wherever_its_output_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry = sealed_root(tmp)
            first = begin_one_shot(registry, Path(tmp)/'anywhere/run-1')
            with self.assertRaisesRegex(ValueError, 'first attempt is the score'):begin_one_shot(registry, Path(tmp)/'elsewhere')
            rerun = begin_one_shot(registry, Path(tmp)/'run-2', 'NVIDIA HTTP 504 in case 3')
            self.assertEqual((first['attempt'], rerun['attempt'], rerun['rerun_reason']), (1, 2, 'NVIDIA HTTP 504 in case 3'))

    def test_concurrent_start_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry = sealed_root(tmp)
            (registry.parent/'.attempt.lock').write_text('')
            with self.assertRaisesRegex(ValueError, 'another held-out attempt'):begin_one_shot(registry, Path(tmp)/'run')

    def test_one_repair_per_attempt_on_unchanged_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, registry = sealed_root(tmp)
            output = Path(tmp)/'run-1'; write(output/'case/run/request.json', '{"intended_behavior": "sealed"}')
            with self.assertRaisesRegex(ValueError, 'not a completed'):begin_repair(registry, output, Path(tmp)/'r0')
            attempt = begin_one_shot(registry, output); finish(registry, attempt['attempt'], output)
            write(output/'case/run/request.json', '{"intended_behavior": "edited with a hint"}')
            with self.assertRaisesRegex(ValueError, 'changed'):begin_repair(registry, output, Path(tmp)/'r1')
            write(output/'case/run/request.json', '{"intended_behavior": "sealed"}')
            self.assertEqual(begin_repair(registry, output, Path(tmp)/'r2')['of_attempt'], attempt['attempt'])
            with self.assertRaisesRegex(ValueError, 'repair budget'):begin_repair(registry, output, Path(tmp)/'r3')


class ReportingTests(unittest.TestCase):
    REGISTRY = dict(cases=[
        dict(case(), files={}), dict(case(id='H4m', case='heading-minimal', variant_of='H4'), files={}),
        dict(id='H5', case='telemetry-timestamp', label='new_mechanism', status='withdrawn', withdrawn_reason='no C# Timestamp'),
        dict(id='H7', case='inventory-rename-key', label='transfer', status='withdrawn', withdrawn_reason='x')])

    def test_cohorts_keep_withdrawn_cases_and_separate_variants(self):
        cohorts = held_out_cohorts(self.REGISTRY)
        self.assertEqual(cohorts['headline'], ['telemetry-heading-frame', 'telemetry-timestamp', 'inventory-rename-key'])
        self.assertEqual(cohorts['new_mechanism'], ['telemetry-heading-frame', 'telemetry-timestamp'])
        self.assertEqual(cohorts['minimal_semantics_variants'], ['heading-minimal'])
        entries, withdrawn = held_out_entries(dict(cases=[c for c in self.REGISTRY['cases'] if c['status'] == 'withdrawn']))
        self.assertEqual((entries, sorted(withdrawn)), ([], ['inventory-rename-key', 'telemetry-timestamp']))

    def test_held_out_run_scores_against_registry_cohorts(self):
        real_run = subprocess.run
        def fake(command, *args, **kwargs):
            return real_run(command, *args, **kwargs) if command[0] == 'git' else mock.Mock(returncode=1)
        entries = [dict(case='telemetry-heading-frame', id='H4', label='new_mechanism', variant_of=None, profile='telemetry-speed-units',
                        source_revision='a'*40, fixture_sha256='x')]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(held_out, 'verify', return_value=self.REGISTRY), \
                mock.patch.object(held_out, 'begin_one_shot', return_value=dict(attempt=1)) as begin, \
                mock.patch.object(held_out, 'finish') as done, \
                mock.patch.object(live_suite, 'held_out_entries', return_value=(entries, {'telemetry-timestamp': 'x'})), \
                mock.patch('patchgen.nvidia_client.credential'), mock.patch.object(live_suite.subprocess, 'run', side_effect=fake):
            registry_file = live_suite.ROOT/'README.md'  # any file inside ROOT
            live_suite.execute(Path(tmp)/'out', **LOCKED_CONFIG, locked=True, held_out=registry_file)
            summary = json.loads((Path(tmp)/'out/summary.json').read_text())
            begin.assert_called_once(); done.assert_called_once()
        self.assertEqual(summary['headline_validated'], '0/3')
        self.assertEqual(summary['validated_by_cohort']['new_mechanism'], '0/2')
        self.assertEqual(summary['model_patch_validation_rate'], 0.0)
        self.assertEqual(summary['held_out_attempt'], 1)

    def test_held_out_run_requires_lock_and_refuses_development_selection(self):
        for kwargs in (dict(locked=False), dict(locked=True, cases=['telemetry-units']), dict(locked=True, full_benchmark=True)):
            config = LOCKED_CONFIG if kwargs['locked'] else dict(backend='ollama', model='ministral-3:8b', strategy='candidate_edits')
            with self.assertRaises(ValueError):
                live_suite.execute(Path('/missing'), config['model'], config['strategy'], backend=config['backend'],
                                   held_out=Path('/missing.json'), **kwargs)
        with self.assertRaises(ValueError):
            live_suite.execute(Path('/missing'), 'ministral-3:8b', rerun_reason='outage')

    def test_repair_refuses_a_different_registry_than_the_scored_run(self):
        from patchgen.nvidia_client import options_for
        from patchgen.live_suite import prompt_fingerprints
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'source'; source.mkdir()
            write(source/'summary.json', json.dumps(dict(status='completed', mode='live_model', automatic_repairs=0,
                locked_configuration='0041', prompt_fingerprints=prompt_fingerprints(), options=options_for(LOCKED_CONFIG['model']),
                results=[], held_out_registry='README.md', held_out_registry_sha256='0'*64, **LOCKED_CONFIG)))
            with mock.patch.object(held_out, 'verify'), mock.patch.object(held_out, 'begin_repair') as begin, \
                    self.assertRaisesRegex(ValueError, 'differs'):
                repair_suite.execute(source, Path(tmp)/'out')
            begin.assert_not_called()


if __name__ == '__main__':
    unittest.main()
