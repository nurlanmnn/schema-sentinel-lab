"""A different score must not hide changed inputs, prompts, or validation gates."""
import json
from pathlib import Path
import tempfile
import unittest
from patchgen.live_comparison import GATE_FUNCTIONS, compare
from patchgen.live_suite import CASES


class ComparisonTests(unittest.TestCase):
    def create(self,root,model='model-a',prompt='2.5'):
        root.mkdir()
        summary=dict(status='completed',mode='live_model',automatic_repairs=0,
            strategy='candidate_edits' if prompt=='2.5' else 'candidate_blocks',prompt_version=prompt,options={'seed':42},
            results=[dict(case=case,generated_patch_validated=False) for case in CASES])
        (root/'summary.json').write_text(json.dumps(summary))
        for case in CASES:
            proposal=root/case/'run/proposal';proposal.mkdir(parents=True)
            for filename,data in [('model.json',{'tag':{'digest':model}}),('input.json',{'case':case}),
                    ('report.json',dict(validation_profile='fixed',oracle_sha256='fixed',
                        benchmark_oracle_sha256='fixed',local_codegen_sha256='fixed'))]:
                (proposal/filename).write_text(json.dumps(data))
            (proposal/'generator-source.py').write_text('\n'.join(f'def {name}():\n    return True\n' for name in GATE_FUNCTIONS))
            request=proposal/'requests/01';request.mkdir(parents=True)
            (request/'request.json').write_text(json.dumps(dict(model=model,messages=[prompt],options={'seed':42})))

    def test_separates_model_prompt_and_confounded_changes(self):
        for model,prompt,expected in [('model-b','2.5','model_comparison'),('model-a','2.8','prompt_development'),
                                      ('model-b','2.8','confounded'),('model-a','2.5','repeat')]:
            with self.subTest(expected=expected),tempfile.TemporaryDirectory() as tmp:
                left,right=Path(tmp)/'left',Path(tmp)/'right'
                self.create(left);self.create(right,model,prompt)
                self.assertEqual(compare(left,right)['comparison_kind'],expected)

    def test_same_prompt_label_does_not_hide_changed_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            left,right=Path(tmp)/'left',Path(tmp)/'right';self.create(left);self.create(right,'model-b')
            path=right/CASES[0]/'run/proposal/requests/01/request.json'
            payload=json.loads(path.read_text());payload['messages']=['silently changed prompt'];path.write_text(json.dumps(payload))
            result=compare(left,right)
            self.assertEqual(result['comparison_kind'],'confounded')
            self.assertTrue(any('request payload' in issue for issue in result['issues']))

    def test_changed_inputs_and_weakened_gate_cannot_be_called_model_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            left,right=Path(tmp)/'left',Path(tmp)/'right';self.create(left);self.create(right,'model-b')
            proposal=right/CASES[0]/'run/proposal'
            (proposal/'input.json').write_text('{}')
            source=proposal/'generator-source.py'
            source.write_text(source.read_text().replace('return True','return False',1))
            result=compare(left,right)
            self.assertEqual(result['comparison_kind'],'confounded')
            self.assertTrue(any('inputs differ' in issue for issue in result['issues']))
            self.assertTrue(any('functions differ' in issue for issue in result['issues']))
