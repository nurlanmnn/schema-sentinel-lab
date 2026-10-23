import copy
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from patchgen.generator import ContractError, check_patch, prompt, validate_input, validate_output, verify_source, apply_and_validate

ROOT = Path(__file__).resolve().parents[2]
CASE = json.loads((ROOT / 'patchgen/fixtures/entity-name-removal/input.json').read_text())


def response(outcome='no_change',diff=''):
    return dict(contract_version='1.0',outcome=outcome,diff=diff,rationale='Explicit reason',confidence=.5,assumptions=[])


@contextmanager
def pinned_source():
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/'source'
        subprocess.run(['git','-C',str(ROOT),'worktree','add','--detach',str(source),CASE['source_revision']],check=True,capture_output=True)
        try:
            yield source
        finally:
            subprocess.run(['git','-C',str(ROOT),'worktree','remove','--force',str(source)],check=True,capture_output=True)


class GeneratorTests(unittest.TestCase):
    def test_all_required_input_fields(self):
        validate_input(CASE)
        for key in CASE:
            bad = copy.deepcopy(CASE); del bad[key]
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_input(bad)
        for key in CASE['change']:
            bad = copy.deepcopy(CASE); del bad['change'][key]
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_input(bad)
        for key in CASE['affected_files'][0]:
            bad = copy.deepcopy(CASE); del bad['affected_files'][0][key]
            with self.subTest(key=key), self.assertRaises(ContractError):
                validate_input(bad)

    def test_reference_excluded(self):
        case = copy.deepcopy(CASE); case['reference_answer'] = 'SECRET_ANSWER'
        case['change']['reference_answer'] = 'SECRET_ANSWER'
        case['affected_files'][0]['reference_answer'] = 'SECRET_ANSWER'
        self.assertNotIn('SECRET_ANSWER',json.dumps(prompt(case)))
        self.assertNotIn('reference/',json.dumps(prompt(case)))

    def test_positions_and_revision(self):
        for key, value in [('source_revision','main'),('contract_version','2.0')]:
            bad=copy.deepcopy(CASE); bad[key]=value
            with self.assertRaises(ContractError): validate_input(bad)
        bad=copy.deepcopy(CASE); bad['affected_files'][0]['positions'][0]['start_line']=0
        with self.assertRaises(ContractError): validate_input(bad)

    def test_outcomes(self):
        for outcome in ('no_change','needs_clarification'):
            self.assertEqual(validate_output(response(outcome))['outcome'],outcome)
        for value in [response('patch'),response('unknown'),response('no_change','bad')]:
            with self.assertRaises(ContractError): validate_output(value)
        for confidence in [True, float('nan'),-1,2]:
            value=response(); value['confidence']=confidence
            with self.assertRaises(ContractError): validate_output(value)

    def test_bad_paths_and_generated_files(self):
        for path in ('../escape','/tmp/escape','generated/python/v1/entity_pb2.py','.git/config','runtimes/python/main.py/../x'):
            diff=f'diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-old\n+new\n'
            with self.subTest(path=path), self.assertRaises(ContractError): check_patch(diff,CASE)
        with self.assertRaises(ContractError): check_patch('not a diff',CASE)

    def test_cli_outcomes_and_missing_input_keep_reports(self):
        with tempfile.TemporaryDirectory() as temp, pinned_source() as source:
            base=Path(temp)
            for outcome in ('no_change','needs_clarification'):
                replay=base/(outcome+'.json'); replay.write_text(json.dumps(response(outcome)))
                output=base/outcome
                result=subprocess.run([sys.executable,'-m','patchgen.generator','--source',str(source),
                    '--response',str(replay),'--output',str(output)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(json.loads((output/'report.json').read_text())['status'],outcome)
                self.assertFalse((output/'workspace').exists())
            output=base/'missing'
            result=subprocess.run([sys.executable,'-m','patchgen.generator','--fixture',str(base/'absent.json'),
                '--output',str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads((output/'report.json').read_text())['status'],'failed')

    def test_stale_source_and_malformed_patch_in_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            repo=Path(temp)/'repo'; repo.mkdir()
            subprocess.run(['git','init',str(repo)],check=True,stdout=subprocess.DEVNULL)
            subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--allow-empty','-m','fixture'],check=True,stdout=subprocess.DEVNULL)
            with self.assertRaisesRegex(ContractError,'stale revision'): verify_source(repo,CASE)
        # Malformed but allowlisted patch is rejected by git before application; source remains unchanged.
        with tempfile.TemporaryDirectory() as temp, pinned_source() as source:
            output=Path(temp)
            bad='diff --git a/runtimes/python/main.py b/runtimes/python/main.py\n--- a/runtimes/python/main.py\n+++ b/runtimes/python/main.py\n@@ -1,100 +1 @@\n-no such context\n+bad\n'
            with self.assertRaises(ContractError): apply_and_validate(source,CASE,response('patch',bad),output,False)
            self.assertEqual((source/'runtimes/python/main.py').read_text(),CASE['affected_files'][0]['source_context'])
            self.assertIn('git apply --check',(output/'validation.log').read_text())
            subprocess.run(['git','-C',str(ROOT),'worktree','remove','--force',str(output/'workspace')],check=False,stderr=subprocess.DEVNULL)


if __name__=='__main__': unittest.main()
