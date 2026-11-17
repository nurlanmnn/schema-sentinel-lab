"""Synthetic AMD HTTP responses only; never read credentials or contact a provider."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import Mock, patch

from patchgen import amd_client as client, generator, live_suite, nvidia_client, pipeline

TOKEN = 'synthetic-amd-secret'
MESSAGES = [dict(role='user', content='{"prompt_version":"test"}')]
ROOT = Path(__file__).resolve().parents[2]


def response(content='{}', **extra):
    return dict(model=client.MODEL, id='synthetic-response', provider='AMD',
                choices=[dict(finish_reason='stop', message=dict(content=content))],
                usage=dict(prompt_tokens=100, completion_tokens=30), **extra)


class AMDTests(unittest.TestCase):
    def test_request_shape_locked_options_and_redacted_evidence(self):
        raw = response('```json\n{"outcome":"no_change"}\n```')
        raw['id'] = TOKEN
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(client, 'credential', return_value=TOKEN), \
             patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(raw).encode())) as http:
            output = Path(tmp)/'request'
            self.assertEqual(client.request_model(MESSAGES, client.MODEL, output), {'outcome': 'no_change'})
            http.assert_called_once()
            request = http.call_args.args[0]
            self.assertEqual(request.full_url, 'https://api.tokenlab.amd.com/v1/chat/completions')
            self.assertEqual(request.get_method(), 'POST')
            self.assertEqual(request.get_header('Authorization'), 'Bearer ' + TOKEN)
            self.assertEqual(request.get_header('Content-type'), 'application/json')
            expected = nvidia_client.options_for(live_suite.LOCKED_CONFIG['model'])
            self.assertEqual(json.loads(request.data), dict(expected, model=client.MODEL,
                                                          messages=MESSAGES, stream=False))
            self.assertEqual(http.call_args.kwargs['timeout'], 600)
            record = json.loads((output/'request-measurement.json').read_text())
            self.assertEqual(record['backend'], 'amd')
            self.assertEqual(record['status'], 'response_received')
            self.assertEqual(record['usage']['prompt_tokens'], 100)
            self.assertTrue(record['json_fence_removed'])
            for path in output.iterdir():
                self.assertNotIn(TOKEN, path.read_text())

    def test_options_equal_locked_gemma_and_are_independent(self):
        expected = nvidia_client.options_for(live_suite.LOCKED_CONFIG['model'])
        self.assertEqual(client.MODELS, ('Gemma-4-31B-IT',))
        self.assertEqual(client.options_for(client.MODEL), expected)
        options = client.options_for(client.MODEL)
        options['temperature'] = 99
        self.assertEqual(client.options_for(client.MODEL), expected)
        self.assertEqual(live_suite.prompt_fingerprints(), live_suite.LOCKED_PROMPT_SHA256)
        self.assertEqual(live_suite.LOCKED_CONFIG['backend'], 'nvidia')

    def test_system_ca_bundle_and_default_fallback(self):
        for exists in (True, False):
            with self.subTest(system_bundle=exists), tempfile.TemporaryDirectory() as tmp, \
                 patch.object(client, 'credential', return_value=TOKEN), \
                 patch.object(client.Path, 'is_file', return_value=exists), \
                 patch.object(client.ssl, 'create_default_context') as context, \
                 patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(response()).encode())) as http:
                client.request_model(MESSAGES, client.MODEL, Path(tmp)/'request')
                if exists:
                    context.assert_called_once_with(cafile='/etc/ssl/cert.pem')
                else:
                    context.assert_called_once_with()
                self.assertIs(http.call_args.kwargs['context'], context.return_value)

    def test_http_errors_redact_body_header_and_exception(self):
        for status in (401, 429, 500, 503):
            error = urllib.error.HTTPError(client.API_URL, status, 'unavailable',
                {'Retry-After': TOKEN}, io.BytesIO(json.dumps(dict(error=TOKEN, user_id='private')).encode()))
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp, \
                 patch.object(client, 'credential', return_value=TOKEN), \
                 patch.object(client.urllib.request, 'urlopen', side_effect=error) as http:
                output = Path(tmp)/'request'
                with self.assertRaises(client.ProviderHTTPError) as caught:
                    client.request_model(MESSAGES, client.MODEL, output)
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertIn('[REDACTED]', str(caught.exception))
                http.assert_called_once()
                record = json.loads((output/'request-measurement.json').read_text())
                self.assertEqual(record['failure_stage'], 'provider_http_error')
                self.assertEqual(record['http_status'], status)
                for path in output.iterdir():
                    self.assertNotIn(TOKEN, path.read_text())
                self.assertNotIn('user_id', (output/'http-error.json').read_text())

    def test_timeout_redacts_exception_and_records_stage(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(client, 'credential', return_value=TOKEN), \
             patch.object(client.urllib.request, 'urlopen', side_effect=TimeoutError(TOKEN)):
            output = Path(tmp)/'request'
            with self.assertRaises(client.ProviderError) as caught:
                client.request_model(MESSAGES, client.MODEL, output)
            self.assertNotIn(TOKEN, str(caught.exception))
            record = json.loads((output/'request-measurement.json').read_text())
            self.assertEqual(record['failure_stage'], 'request_timeout')
            self.assertNotIn(TOKEN, json.dumps(record))

    def test_identity_substitution_is_rejected_and_redacted(self):
        raw = response()
        raw['model'] = TOKEN
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(client, 'credential', return_value=TOKEN), \
             patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(raw).encode())):
            output = Path(tmp)/'request'
            with self.assertRaises(client.ProviderIdentityError) as caught:
                client.request_model(MESSAGES, client.MODEL, output)
            self.assertNotIn(TOKEN, str(caught.exception))
            record = json.loads((output/'request-measurement.json').read_text())
            self.assertEqual(record['failure_stage'], 'provider_identity_mismatch')

    def test_unapproved_model_stops_before_credentials_or_http(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, 'credential') as credential, \
             patch.object(client.urllib.request, 'urlopen') as http:
            with self.assertRaises(client.ProviderError):
                client.request_model([], 'unapproved/model', Path(tmp)/'request')
            credential.assert_not_called()
            http.assert_not_called()

    def test_credential_file_permissions_are_checked_without_real_key_access(self):
        key_file = Mock()
        key_file.is_file.return_value = True
        key_file.stat.return_value.st_mode = 0o600
        key_file.read_text.return_value = TOKEN + '\n'
        with patch.object(client, 'KEY_FILE', key_file), patch.dict('os.environ', {'AMD_API_KEY': ''}):
            self.assertEqual(client.credential(), TOKEN)
            key_file.stat.return_value.st_mode = 0o644
            key_file.read_text.reset_mock()
            with self.assertRaisesRegex(client.ProviderError, 'owner-only'):
                client.credential()
            key_file.read_text.assert_not_called()

    def test_generator_dispatch_stops_after_first_provider_error(self):
        case = json.loads((ROOT/'patchgen/fixtures/entity-name-removal/input.json').read_text())
        with tempfile.TemporaryDirectory() as tmp, patch.object(client, 'credential', return_value=TOKEN), \
             patch.object(client.urllib.request, 'urlopen', side_effect=urllib.error.HTTPError(
                 client.API_URL, 503, 'unavailable', {}, io.BytesIO(b'{}'))) as http:
            output = Path(tmp)
            with self.assertRaisesRegex(generator.ContractError, 'HTTP 503'):
                generator.generate(case, client.MODEL, 'unused', output, 'candidate_edits', backend='amd')
            http.assert_called_once()
            self.assertEqual(json.loads((output/'model.json').read_text())['options'], client.options_for(client.MODEL))


class BackendCLITests(unittest.TestCase):
    def test_pipeline_accepts_amd_and_openrouter_cohere(self):
        for backend, model in (('amd', client.MODEL), ('openrouter', 'cohere/north-mini-code:free')):
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as tmp, \
                 patch('sys.argv', ['pipeline', '--output', str(Path(tmp)/'out'), '--generate',
                                    '--backend', backend, '--model', model]), \
                 patch('patchgen.' + backend + '_client.credential') as credential, \
                 patch.object(pipeline, 'run', return_value=dict(status='validation_passed')) as run, \
                 patch('builtins.print'):
                self.assertEqual(pipeline.main(), 0)
                credential.assert_called_once()
                self.assertEqual(run.call_args.args[6], model)
                self.assertEqual(run.call_args.args[8], backend)

    def test_live_suite_cli_accepts_amd_and_defaults_to_its_model(self):
        for explicit in (False, True):
            args = ['live_suite', '--output', 'unused', '--backend', 'amd']
            if explicit:
                args += ['--model', client.MODEL]
            with self.subTest(explicit=explicit), patch('sys.argv', args), \
                 patch.object(live_suite, 'execute', return_value=0) as execute:
                self.assertEqual(live_suite.main(), 0)
                self.assertEqual(execute.call_args.args[1], client.MODEL)
                self.assertEqual(execute.call_args.kwargs['backend'], 'amd')
