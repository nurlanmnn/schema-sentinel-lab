"""Fresh selection, split denominators, seals and frozen prompts; no model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen import live_suite, fresh_cases, fresh_manifest, fresh_attempts
from patchgen.generator import LOCAL_MODELS, OPENROUTER_MODEL
from patchgen.nvidia_client import MODELS as NVIDIA_MODELS
from run_benchmark import CASES as DEVELOPMENT


class FreshSuiteTests(unittest.TestCase):
    def test_membership_and_locked_prompts(self):
        self.assertEqual(live_suite.FRESH_CASES,fresh_cases.PROFILES)
        self.assertEqual(len(live_suite.FRESH_CASES),5)
        self.assertFalse(set(live_suite.FRESH_CASES)&set(DEVELOPMENT))
        self.assertFalse(set(live_suite.FRESH_CASES)&set(live_suite.CASES+live_suite.ADDITIONAL_CASES))
        live_suite.require_locked_prompts()

    def execute_fake(self, output, model='ministral-3:8b', strategy='candidate_edits', backend='ollama', **kwargs):
        if kwargs.get('fresh'):
            kwargs.setdefault('sample', 1)
        result=dict(status='validation_passed',generated_patch_validated=True,model_requests=3,generation_seconds=1)
        with patch.object(fresh_attempts, 'DEFAULT', output.parent/'attempts.jsonl'), \
             patch('builtins.print'), patch.object(fresh_manifest,'verify',return_value={}) as verified, \
             patch.object(live_suite.subprocess,'run') as process, \
             patch.object(live_suite,'collect',return_value=result), \
             patch.object(live_suite.subprocess,'check_output',return_value='a'*40), \
             patch('patchgen.nvidia_client.credential') as nvidia, \
             patch('patchgen.openrouter_client.credential') as openrouter, \
             patch('patchgen.amd_client.credential') as amd, \
             patch('patchgen.selfhosted_client.credential') as selfhosted, \
             patch.object(Path,'read_bytes',autospec=True,return_value=b'test sealed inputs'):
            process.return_value.returncode=0
            code=live_suite.execute(output,model,strategy,backend=backend,**kwargs)
            summary=json.loads((output/'summary.json').read_text())
            self.assertEqual(code,0)
            verified.assert_called_once()
            self.assertEqual(process.call_count,summary['planned_cases'])
            for call in process.call_args_list:
                command=call.args[0]
                self.assertEqual(command[command.index('--backend')+1],backend)
                self.assertEqual(command[command.index('--model')+1],model)
                self.assertEqual(command[command.index('--strategy')+1],strategy)
            if backend=='nvidia':nvidia.assert_called_once()
            if backend=='openrouter':openrouter.assert_called_once()
            if backend=='amd':amd.assert_called_once()
            if backend=='selfhosted':selfhosted.assert_called_once()
            return summary

    def test_fresh_runs_exactly_five_with_all_allowed_backends_models_and_strategies(self):
        configs=[('ollama',m) for m in LOCAL_MODELS]+[('openrouter',OPENROUTER_MODEL)]+[('nvidia',m) for m in NVIDIA_MODELS]+[('amd','Gemma-4-31B-IT')]
        strategies=('candidate_edits','candidate_semantic_edits','candidate_blocks','candidate_semantic_blocks')
        with tempfile.TemporaryDirectory() as tmp:
            index=0
            for backend,model in configs:
                for strategy in strategies:
                    with self.subTest(backend=backend,model=model,strategy=strategy):
                        summary=self.execute_fake(Path(tmp)/str(index),model,strategy,backend,fresh=True)
                        self.assertEqual(set(summary['case_split']),set(live_suite.FRESH_CASES))
                        self.assertEqual(set(summary['case_split'].values()),{'fresh_screen'})
                        self.assertEqual(summary['validated_by_split']['fresh_screen'],'5/5')
                        self.assertEqual(summary['validated_by_split']['development'],'0/0')
                        index+=1

    def test_locked_fresh_and_explicit_case_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary=self.execute_fake(Path(tmp)/'locked',**live_suite.LOCKED_CONFIG,fresh=True,locked=True)
            self.assertEqual(summary['locked_configuration'],'0045')
            self.assertEqual(summary['backend'],'selfhosted')
            self.assertEqual(summary['model'],'inkling-2-mini-q8_0')
            self.assertEqual(summary['prompt_fingerprints'],live_suite.LOCKED_PROMPT_SHA256)
            summary=self.execute_fake(Path(tmp)/'single',cases=[live_suite.FRESH_CASES[0]])
            self.assertEqual(summary['validated_by_split']['fresh_screen'],'1/1')
            self.assertEqual(summary['planned_cases'],1)

    def test_unsealed_or_changed_inputs_refuse_before_credentials_or_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            for options in (dict(fresh=True,sample=1),dict(cases=[live_suite.FRESH_CASES[0]])):
                with patch.object(fresh_manifest,'verify',side_effect=ValueError('unsealed')), \
                     patch('patchgen.nvidia_client.credential') as credential, \
                     patch.object(live_suite.subprocess,'run') as process:
                    with self.assertRaisesRegex(ValueError,'unsealed'):
                        live_suite.execute(Path(tmp)/'out',NVIDIA_MODELS[0],backend='nvidia',**options)
                    credential.assert_not_called();process.assert_not_called()
                    self.assertFalse((Path(tmp)/'out').exists())

    def test_fresh_cannot_combine_with_other_selection_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for options in (dict(held_out=Path(tmp)/'not-read'),dict(cases=[live_suite.FRESH_CASES[0]]),dict(full_benchmark=True)):
                with self.assertRaisesRegex(ValueError,'--fresh runs exactly'):
                    live_suite.execute(Path(tmp)/'out','ministral-3:8b',fresh=True,**options)

    def test_provider_failure_keeps_all_five_in_fresh_denominator(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fresh_attempts, 'DEFAULT', Path(tmp)/'attempts.jsonl'), patch('builtins.print'), patch.object(fresh_manifest,'verify',return_value={}), \
             patch.object(live_suite.subprocess,'run') as process, \
             patch.object(live_suite,'collect',return_value=dict(status='provider_unavailable',generated_patch_validated=False,model_requests=1,generation_seconds=1)), \
             patch.object(live_suite.subprocess,'check_output',return_value='a'*40), \
             patch.object(Path,'read_bytes',autospec=True,return_value=b'sealed'):
            process.return_value.returncode=1
            output=Path(tmp)/'out'
            self.assertEqual(live_suite.execute(output,'ministral-3:8b',fresh=True,sample=1),1)
            summary=json.loads((output/'summary.json').read_text())
            self.assertEqual(summary['validated_by_split']['fresh_screen'],'0/5')
            self.assertEqual(summary['planned_cases'],5)
            self.assertEqual(summary['model_patch_validation_rate'],0/5)
            self.assertEqual(summary['infrastructure_failures'],1)
            self.assertEqual(summary['model_failures'],0)

    def test_fresh_requires_positive_sample_before_verification_and_sample_is_fresh_only(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fresh_manifest, 'verify') as verify:
            for sample in (None, 0, -1, True):
                with self.subTest(sample=sample), self.assertRaisesRegex(ValueError, '--sample'):
                    live_suite.execute(Path(tmp)/'out', 'ministral-3:8b', fresh=True, sample=sample)
            with self.assertRaisesRegex(ValueError, 'only to --fresh'):
                live_suite.execute(Path(tmp)/'out', 'ministral-3:8b', sample=1)
            verify.assert_not_called()

    def test_duplicate_fresh_attempt_is_refused_before_credentials_or_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'first'
            first = self.execute_fake(output, fresh=True)
            original = (Path(tmp)/'attempts.jsonl').read_bytes()
            with patch.object(fresh_attempts, 'DEFAULT', Path(tmp)/'attempts.jsonl'), \
                 patch.object(fresh_manifest, 'verify', return_value={}), \
                 patch.object(Path, 'read_bytes', return_value=b'test sealed inputs'), \
                 patch('patchgen.nvidia_client.credential') as credential, \
                 patch.object(live_suite.subprocess, 'run') as process:
                # Backend is deliberately not part of the attempt identity.
                with self.assertRaisesRegex(ValueError, 'already attempted'):
                    live_suite.execute(Path(tmp)/'duplicate', 'ministral-3:8b', fresh=True, sample=1)
                process.assert_not_called(); credential.assert_not_called()
            self.assertFalse((Path(tmp)/'duplicate').exists())
            self.assertEqual((Path(tmp)/'attempts.jsonl').read_bytes(), original)
            rerun = self.execute_fake(Path(tmp)/'rerun', fresh=True, rerun_reason='transport investigation')
            rows = [json.loads(line) for line in (Path(tmp)/'attempts.jsonl').read_text().splitlines()]
            self.assertEqual(rows[0], first['fresh_attempt'])
            self.assertFalse(rows[0]['rerun'])
            self.assertTrue(rows[1]['rerun'])
            self.assertEqual(rows[1]['original_attempt'], rows[0]['attempt'])
            self.assertEqual(rows[1], rerun['fresh_attempt'])
            self.execute_fake(Path(tmp)/'sample2', fresh=True, sample=2)
            self.assertTrue((Path(tmp)/'attempts.jsonl').read_bytes().startswith(original))

    def test_reservation_survives_credential_failure(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(fresh_attempts, 'DEFAULT', Path(tmp)/'attempts.jsonl'), \
             patch.object(fresh_manifest, 'verify', return_value={}), \
             patch.object(Path, 'read_bytes', return_value=b'sealed'), \
             patch('patchgen.nvidia_client.credential', side_effect=ValueError('no key')), \
             patch.object(live_suite.subprocess, 'run') as process:
            with self.assertRaisesRegex(ValueError, 'no key'):
                live_suite.execute(Path(tmp)/'out', NVIDIA_MODELS[0], backend='nvidia', fresh=True, sample=1)
            rows = (Path(tmp)/'attempts.jsonl').read_text().splitlines()
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0])['sample'], 1)
            self.assertFalse((Path(tmp)/'out').exists())
            process.assert_not_called()

    def test_concurrent_reservations_allow_only_one_original(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'attempts.jsonl'
            def reserve(index):
                try:
                    return fresh_attempts.begin(Path(tmp)/str(index), 'backend', 'model', 'strategy', 1, 'digest', path=path)
                except ValueError:
                    return None
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(reserve, range(4)))
            self.assertEqual(sum(row is not None for row in results), 1)
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_ledger_records_required_metadata_and_rejects_blank_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp)/'attempts.jsonl'
            row = fresh_attempts.begin(Path(tmp)/'out', 'nvidia', 'model', 'strategy', 3, 'digest', path=ledger)
            self.assertEqual(row['manifest_sha256'], 'digest')
            self.assertEqual(row['sample'], 3)
            self.assertEqual(row['backend'], 'nvidia')
            self.assertEqual(row['output_dir'], str((Path(tmp)/'out').resolve()))
            self.assertTrue(row['timestamp'].endswith('+00:00'))
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                fresh_attempts.begin(Path(tmp)/'rerun', 'nvidia', 'model', 'strategy', 3, 'digest', ' ', path=ledger)



class FreshManifestTests(unittest.TestCase):
    def test_verification_compares_membership_hashes_baselines_and_fingerprints(self):
        # No invocation of seal: the production seal remains a future explicit action.
        value=dict(manifest_version='1.0',files={'fixture':'a'},cases=['five cases'],prompt_fingerprints={'one_shot':'b'})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json'
            with self.assertRaisesRegex(ValueError,'unsealed'):fresh_manifest.verify(path)
            path.write_text(json.dumps(value))
            with patch.object(fresh_manifest,'snapshot',return_value=value):self.assertEqual(fresh_manifest.verify(path),value)
            for key,new in [('files',{}),('cases',[]),('prompt_fingerprints',{})]:
                wrong={**value,key:new}
                with patch.object(fresh_manifest,'snapshot',return_value=wrong),self.assertRaisesRegex(ValueError,'mismatch'):
                    fresh_manifest.verify(path)
            path.unlink();path.symlink_to(Path(tmp)/'absent')
            with self.assertRaisesRegex(ValueError,'unsealed'):fresh_manifest.verify(path)

    def test_snapshot_includes_every_authored_input_and_baseline(self):
        value=fresh_manifest.snapshot()
        self.assertEqual(value['split'],'fresh_screen')
        self.assertEqual([row['case'] for row in value['cases']],list(live_suite.FRESH_CASES))
        self.assertEqual(value['prompt_fingerprints'],live_suite.prompt_fingerprints())
        for row in value['cases']:
            name=row['case']
            self.assertIn('proto/v1/entity.proto',row['baseline_sha256'])
            self.assertIn('runtimes/csharp/main.cs',row['baseline_sha256'])
            for directory in ('fixtures','reference'):
                for path in (fresh_manifest.ROOT/'patchgen'/directory/name).rglob('*'):
                    if path.is_file():self.assertIn(str(path.relative_to(fresh_manifest.ROOT)),value['files'])
        self.assertIn('patchgen/fresh_oracle.py',value['files'])
        self.assertIn('patchgen/live_suite.py',value['files'])
        self.assertIn('patchgen/pipeline-requirements.txt',value['files'])
        self.assertNotIn('patchgen/live_analysis.py',value['files'])
        self.assertNotIn('patchgen/inventory_evolution.py',value['files'])
        rendered = fresh_manifest.rendered_inputs(fresh_manifest.ROOT, [fresh_cases.fixture(n) for n in live_suite.FRESH_CASES])
        for row in value['cases']:
            self.assertEqual(row['prepared_input_sha256'], rendered[row['case']]['prepared_input_sha256'])
            hashes = row['rendered_prompt_sha256']['candidate_semantic_blocks']
            self.assertEqual(set(hashes), set(fresh_cases.EDITS[row['case']]))
            self.assertEqual(row['rendered_prompt_sha256'], rendered[row['case']]['rendered_prompt_sha256'])
            self.assertTrue(all(len(digest) == 64 for digest in hashes.values()))
        self.assertIn('testbed/pubsub/broker.py',value['files'])
