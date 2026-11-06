"""Repair rounds must stay bounded, leak-free and separate from first-pass results."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from patchgen import repair_suite
from patchgen.feedback_blocks import make_prompt
from patchgen.generator import ContractError, generate
from patchgen.live_suite import LOCKED_CONFIG, LOCKED_PROMPT_SHA256, prompt_fingerprints
from patchgen.nvidia_client import options_for
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
    return dict(status='completed', mode='live_model', automatic_repairs=0, locked_configuration='0041',
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
                           dict(options=dict(OPTIONS, temperature=1))):
                write(root/'summary.json', {**good, **change})
                with self.assertRaises(ValueError):require_locked_source(root)
            # The summary is not enough: retained requests must show the locked sampling was sent.
            write(root/'summary.json', good)
            write(root/'case/run/proposal/requests/01/request.json', dict(OPTIONS, model=LOCKED_CONFIG['model'], temperature=1))
            with self.assertRaises(ValueError):require_locked_source(root)

    def test_round_bound(self):
        for limit in (0, 3):
            with self.assertRaises(ValueError):execute(Path('/missing'), Path('/missing-output'), limit)

    def test_hosted_repair_strategy_is_nvidia_only(self):
        from patchgen.generator import OPENROUTER_MODEL
        with tempfile.TemporaryDirectory() as tmp, mock.patch('patchgen.openrouter_client.credential') as credential:
            # A valid OpenRouter model still cannot use hosted repair feedback.
            with self.assertRaises(ContractError):
                generate(CASE, OPENROUTER_MODEL, None, Path(tmp), 'candidate_semantic_feedback_blocks', 'openrouter')
            credential.assert_not_called()

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
            self.assertEqual(summary['first_pass_validated'], 1)
            self.assertEqual(summary['validated_within_rounds'], {'1': 3, '2': 3})
            self.assertEqual(summary['first_pass_stages'],
                             dict(good='validated', bad='compilation', incomplete='incomplete_acceptance'))
            self.assertEqual(summary['repair_model_requests'], 2)
            self.assertTrue(summary['human_approval_required'])


if __name__ == '__main__':
    unittest.main()
