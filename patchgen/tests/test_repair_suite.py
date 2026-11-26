"""Repair rounds must stay bounded, leak-free and separate from first-pass results."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from patchgen import generator, nvidia_client, pipeline, repair_suite, selfhosted_client
from patchgen.feedback_blocks import make_prompt
from patchgen.generator import ContractError, generate
from patchgen.live_suite import LOCKED_CONFIG, LOCKED_DECISION, LOCKED_PROMPT_SHA256, prompt_fingerprints
from patchgen.selfhosted_client import options_for
from patchgen.repair_suite import build_feedback, compiler_lines, execute, failure_stage, require_locked_source

FILE = dict(path='runtimes/csharp/main.cs', language='csharp', source_context='old = 1;\n',
            positions=[dict(start_line=1, end_line=1, reason='candidate')])
CASE = dict(contract_version='1.0', source_revision='a'*40, intended_behavior='migration',
            change=dict(id='change', category='field_renamed', old_schema='old', new_schema='new', schema_path='proto/a.proto'),
            affected_files=[FILE])


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value))


OPTIONS = options_for(LOCKED_CONFIG['model'])


def locked_summary(results):
    return dict(status='completed', mode='live_model', automatic_repairs=0, locked_configuration=LOCKED_DECISION,
                prompt_fingerprints=prompt_fingerprints(), options=OPTIONS, results=results, **LOCKED_CONFIG)


def rejected_proposal(root, log='', oracle=None, edit=None):
    write(root/'report.json', dict(status='failed', error='command failed: pip install output and test names'))
    write(root/'requests/01/edit-validation.json', edit or dict(status='passed'))
    write(root/'requests/01/parsed-response.json', dict(outcome='patch'))
    if log:write(root/'validation.log', log)
    if oracle:write(root/'telemetry/report.json', oracle)


class RepairSuiteTests(unittest.TestCase):
    def test_locked_prompts_are_frozen(self):
        # Changing prompt text must fail here and require a new decision.
        self.assertEqual(prompt_fingerprints(), LOCKED_PROMPT_SHA256)
        with mock.patch.dict(LOCKED_CONFIG, backend='nvidia', model='google/gemma-4-31b-it'):
            old = prompt_fingerprints()
        for key in ('one_shot', 'repair'):
            self.assertEqual(old[key], LOCKED_PROMPT_SHA256[key])
        self.assertEqual(old['protocol'], '6f648b9cc530f966c237997ee5c6f690643a02f0fbab36d61fe0d6b82d948dde')
        self.assertNotEqual(old['protocol'], LOCKED_PROMPT_SHA256['protocol'])

    def test_semantic_repair_prompt_keeps_locked_guidance(self):
        from patchgen.generator import SEMANTIC_GUIDANCE
        case = dict(CASE, model_feedback=dict(source_revision='a'*40, change_id='change',
            files={FILE['path']: dict(previous_response={}, validation_diagnostics=['CS1503'])}))
        messages, _ = make_prompt(case, FILE, semantic=True)
        self.assertIn(SEMANTIC_GUIDANCE, messages[0]['content'])
        self.assertEqual(json.loads(messages[1]['content'])['prompt_version'], '3.1-feedback')

    def test_compiler_feedback_hides_evaluator_tests_and_local_paths(self):
        log = ('/Users/me/My Lab/run/workspace/runtimes/csharp/main.cs(21,78): error CS1503: bad [/Users/me/x/App.csproj]\n'
               '/Users/me/My Lab/run/workspace/testbed/tests/test_hidden.py:3: SyntaxError: expected 96.6\n')
        kept, withheld = compiler_lines(log, [FILE['path']])
        self.assertEqual(kept, ['runtimes/csharp/main.cs(21,78): error CS1503: bad'])
        self.assertEqual(withheld, 1)

    def test_compiler_feedback_requires_the_diagnostic_location_to_be_edited(self):
        # An evaluator-test error that merely mentions an edited path stays hidden.
        log = '/w/workspace/testbed/tests/Hidden.cs(3,1): error CS0103: runtimes/csharp/main.cs expected secret-77\n'
        self.assertEqual(compiler_lines(log, [FILE['path']]), ([], 1))

    def test_python_syntax_errors_from_the_report_reach_the_owning_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = dict(FILE, path='runtimes/python/main.py', language='python')
            rejected_proposal(root)
            write(root/'report.json', dict(status='failed', error='unexpected indent (main.py, line 85)'))
            feedback, _ = build_feedback(root, dict(CASE, affected_files=[python]))
            self.assertEqual(feedback['files'][python['path']]['validation_diagnostics'],
                             ['SyntaxError: unexpected indent (runtimes/python/main.py, line 85)'])

    def test_feedback_shares_fixed_oracle_verdicts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Secrets planted inside the error string itself, as real oracles can do.
            rejected_proposal(root, oracle=dict(status='failed', expected=[96.6], vectors=['vector-secret'],
                error='csharp: decoded fields differ for msg-secret-42, expected 96.6 at case 1'))
            feedback, _ = build_feedback(root, CASE)
            text = json.dumps(feedback)
            self.assertIn('telemetry runtime check failed at authored case 1 in the csharp service', text)
            for leaked in ('96.6', 'secret', 'pip install'):self.assertNotIn(leaked, text)
            write(root/'report.json', dict(status='validation_passed'))
            with self.assertRaises(ValueError):build_feedback(root, CASE)

    def test_fresh_oracle_verdict_reaches_feedback_without_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rejected_proposal(root)
            write(root/'fresh/report.json', dict(status='failed', expected={'speed': 12.5},
                  error='typescript: fresh wire/behavior mismatch at vector 1: fields speed=12.5'))
            text = json.dumps(build_feedback(root, CASE)[0])
            self.assertIn('fresh runtime check failed in the typescript service', text)
            for leaked in ('12.5', 'speed', 'vector'):self.assertNotIn(leaked, text)

    def test_failure_stages_are_reported_separately(self):
        result = lambda status='failed', requests=1, edit='passed': dict(status=status, model_requests=requests,
                                                                        requests=[dict(edit_validation=dict(status=edit))])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(failure_stage(root, result('provider_unavailable')), 'provider_unavailable')
            self.assertEqual(failure_stage(root, result(requests=0)), 'no_model_request')
            # Passing checks alone never classify as validated; acceptance needs the full boolean.
            self.assertEqual(failure_stage(root, result('validation_passed')), 'incomplete_acceptance')
            self.assertEqual(failure_stage(root, result(edit='failed')), 'response_or_edit_contract')
            write(root/'run/proposal/telemetry/report.json', dict(status='failed'))
            self.assertEqual(failure_stage(root, result()), 'runtime_semantics')
            write(root/'run/proposal/validation.log', 'x.ts(1,1): error TS2322: bad')
            self.assertEqual(failure_stage(root, result()), 'compilation')

    def test_source_must_be_locked_unrepaired_with_unchanged_prompts(self):
        good = locked_summary([])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root/'summary.json', good); require_locked_source(root)
            for change in (dict(locked_configuration=None), dict(automatic_repairs=1), dict(model='ministral-3:8b'),
                           dict(prompt_fingerprints=dict(one_shot='x', repair='y')), dict(status='running'),
                           dict(options=dict(OPTIONS, temperature=0.5))):
                write(root/'summary.json', {**good, **change})
                with self.assertRaises(ValueError):require_locked_source(root)
            # The summary is not enough: retained requests must show the locked sampling was sent.
            write(root/'summary.json', good)
            request = root/'case/run/proposal/requests/01/request.json'
            write(request, dict(OPTIONS, model=LOCKED_CONFIG['model']))
            require_locked_source(root)
            write(request, dict(OPTIONS, model=LOCKED_CONFIG['model'], temperature=0.5))
            with self.assertRaises(ValueError):require_locked_source(root)

    def test_round_bound(self):
        for limit in (0, 3):
            with self.assertRaises(ValueError):execute(Path('/missing'), Path('/missing-output'), limit)

    def test_hosted_repair_strategy_refuses_openrouter(self):
        from patchgen.generator import OPENROUTER_MODEL
        with tempfile.TemporaryDirectory() as tmp, mock.patch('patchgen.openrouter_client.credential') as credential:
            # A valid OpenRouter model still cannot use hosted repair feedback.
            with self.assertRaises(ContractError):
                generate(CASE, OPENROUTER_MODEL, None, Path(tmp), 'candidate_semantic_feedback_blocks', 'openrouter')
            credential.assert_not_called()

    def test_feedback_request_uses_selfhosted_and_keeps_nvidia_working(self):
        reply = dict(outcome='needs_clarification', edits=[], rationale='synthetic clarification',
                     confidence=0.5, assumptions=[], candidate_reviews={'C001': dict(decision='unaffected', reason='synthetic')})
        for backend, client, model in (('selfhosted', selfhosted_client, LOCKED_CONFIG['model']),
                                      ('nvidia', nvidia_client, 'google/gemma-4-31b-it')):
            raw = dict(model=model, choices=[dict(finish_reason='stop', message=dict(content=json.dumps(reply)))])
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write(root/'input.json', CASE)
                write(root/'feedback.json', dict(source_revision=CASE['source_revision'], change_id=CASE['change']['id'],
                    files={FILE['path']: dict(previous_response={}, validation_diagnostics=['CS1503'])}))
                args = ['generator', '--fixture', str(root/'input.json'), '--output', str(root/'out'),
                        '--backend', backend, '--model', model, '--strategy', 'candidate_semantic_feedback_blocks',
                        '--feedback', str(root/'feedback.json')]
                with mock.patch('sys.argv', args), mock.patch('builtins.print'), \
                     mock.patch.object(generator, 'verify_source'), \
                     mock.patch.object(selfhosted_client, 'api_url', return_value=selfhosted_client.DEFAULT_URL), \
                     mock.patch.object(client, 'credential', return_value='synthetic-token') as credential, \
                     mock.patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(raw).encode())) as http:
                    self.assertEqual(generator.main(), 0)
                    credential.assert_called()
                    http.assert_called_once()
                    request = http.call_args.args[0]
                    self.assertEqual(request.full_url, selfhosted_client.DEFAULT_URL if backend == 'selfhosted' else nvidia_client.API_URL)
                    body = json.loads(request.data)
                    self.assertEqual(body, dict(client.options_for(model), model=model, messages=body['messages'], stream=False))
                    payload = json.loads(body['messages'][1]['content'])
                    self.assertEqual(payload['prompt_version'], '3.1-feedback')
                    self.assertEqual(payload['previous_attempt']['validation_diagnostics'], ['CS1503'])
                report = json.loads((root/'out/report.json').read_text())
                self.assertEqual((report['mode'], report['status']), ('live_model_feedback', 'needs_clarification'))

    def test_pipeline_accepts_locked_and_nvidia_feedback(self):
        for backend, model in (('selfhosted', LOCKED_CONFIG['model']), ('nvidia', 'google/gemma-4-31b-it')):
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as tmp, \
                 mock.patch('sys.argv', ['pipeline', '--output', str(Path(tmp)/'out'), '--generate',
                    '--backend', backend, '--model', model, '--strategy', 'candidate_semantic_feedback_blocks',
                    '--feedback', str(Path(tmp)/'feedback.json')]), \
                 mock.patch('patchgen.' + backend + '_client.credential') as credential, \
                 mock.patch.object(pipeline, 'run', return_value=dict(status='validation_passed')) as run, \
                 mock.patch('builtins.print'):
                self.assertEqual(pipeline.main(), 0)
                credential.assert_called_once()
                self.assertEqual(run.call_args.args[4], 'candidate_semantic_feedback_blocks')
                self.assertEqual(run.call_args.args[6:], (model, Path(tmp)/'feedback.json', backend))

    def test_repaired_passes_never_count_as_first_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'source', Path(tmp)/'output'
            rows = []
            # 'incomplete' passed its checks without full acceptance (e.g. no review bundle).
            for name, status, passed in (('good', 'validation_passed', True), ('bad', 'failed', False),
                                         ('incomplete', 'validation_passed', False)):
                rows.append(dict(case=name, status=status, generated_patch_validated=passed,
                                 model_requests=1, requests=[dict(edit_validation=dict(status='passed'))]))
                proposal = source/name/'run/proposal'
                write(proposal/'input.json', CASE); write(source/name/'run/request.json', CASE)
                rejected_proposal(proposal, log='runtimes/csharp/main.cs(1,1): error CS1503: bad')
            write(source/'summary.json', locked_summary(rows))
            calls = []
            def fake_pipeline(command, **_):
                calls.append(command)
                target = Path(command[command.index('--output') + 1]).parent
                write(target/'run/report.json', dict(status='validation_passed', proposal_report=dict(mode='live_model_feedback')))
                write(target/'run/proposal/report.json', dict(status='validation_passed'))
                write(target/'run/proposal/requests/01/request.json', {})
                write(target/'review/index.html', 'review')
                return mock.Mock(returncode=0)
            with mock.patch.object(repair_suite.subprocess, 'run', side_effect=fake_pipeline):
                self.assertEqual(execute(source, output), 0)
            summary = json.loads((output/'summary.json').read_text())
            self.assertEqual(len(calls), 2)
            self.assertIn('candidate_semantic_feedback_blocks', calls[0])
            for command in calls:
                self.assertEqual(command[command.index('--backend')+1], 'selfhosted')
                self.assertEqual(command[command.index('--model')+1], 'inkling-2-mini-q8_0')
            self.assertEqual(summary['locked_configuration'], '0045')
            self.assertEqual(summary['first_pass_validated'], 1)
            self.assertEqual(summary['validated_within_rounds'], {'1': 3, '2': 3})
            self.assertEqual(summary['first_pass_stages'],
                             dict(good='validated', bad='compilation', incomplete='incomplete_acceptance'))
            self.assertEqual(summary['repair_model_requests'], 2)
            self.assertTrue(summary['human_approval_required'])


if __name__ == '__main__':
    unittest.main()
