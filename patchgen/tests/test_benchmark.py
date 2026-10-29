import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen import benchmark
from patchgen.generator import ContractError,load_validation_profile,edit_prompt


class BenchmarkTests(unittest.TestCase):
    def test_exact_enum_seed_recreated_without_changing_head(self):
        from patchgen.generator import command
        before=command(['git','rev-parse','HEAD'],benchmark.ROOT)
        seed=benchmark.prepare_enum_seed()
        self.assertEqual(seed['enum_seed_revision'],'d573c55e0d157f6b8c909df81b189aadd9040c1b')
        self.assertEqual(before,command(['git','rev-parse','HEAD'],benchmark.ROOT))

    def test_case_failure_does_not_skip_remaining_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_run(args,**kwargs):
                output=Path(args[args.index('--output')+1]);output.mkdir()
                status='failed' if output.name=='entity-name-rename' else 'validation_passed'
                (output/'report.json').write_text(json.dumps(dict(status=status,mode='live_model')))
                return type('Result',(),{'returncode':1 if status=='failed' else 0})()
            target=Path(tmp)/'run'
            seed=json.loads((benchmark.ROOT/'patchgen/fixtures/benchmark-seed.json').read_text())
            with patch('sys.argv',['benchmark','--output',str(target)]),patch('patchgen.benchmark.prepare_enum_seed',return_value=seed),patch('patchgen.benchmark.subprocess.run',side_effect=fake_run):
                self.assertEqual(benchmark.main(),1)
            summary=json.loads((target/'summary.json').read_text())
            self.assertEqual(len(summary['results']),3)
            self.assertEqual(summary['results'][-1]['status'],'validation_passed')

    def test_current_required_sites_match_independent_inventory(self):
        for name in ('entity-name-rename','v2-identifier-bytes'):
            case=json.loads((benchmark.ROOT/'patchgen/fixtures'/name/'runtime-input.json').read_text())
            expected=json.loads((benchmark.ROOT/'patchgen/reference'/name/'expected.json').read_text())
            sites={(f['path'],p['start_line']) for f in case['affected_files'] for p in f['positions']}
            truth={(f['path'],line) for f in expected['runtime_sites'] for line in f['lines']}
            self.assertEqual(sites,truth)

    def test_rename_profile_pins_schema_and_excludes_tests_from_prompts(self):
        case=json.loads((benchmark.ROOT/'patchgen/fixtures/entity-name-rename/runtime-input.json').read_text())
        profile,diff=load_validation_profile(case,'entity-name-rename')
        for file in case['affected_files']:
            encoded=json.dumps(edit_prompt(case,file,'migration_edits'))
            self.assertNotIn('test_evidence.py',encoded)
            self.assertNotIn('expected.patch',encoded)
        case['change']['new_schema']+='\n'
        with self.assertRaises(ContractError):load_validation_profile(case,'entity-name-rename')


if __name__=='__main__':unittest.main()
