"""Synthetic self-hosted HTTP responses only; never contact a server."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from patchgen import selfhosted_client as client, live_suite

MESSAGES = [dict(role='user', content='{"prompt_version":"test"}')]


def response(content='{}', model=client.MODEL, finish='stop'):
    return dict(model=model, id='synthetic-response', system_fingerprint='b1234-abc',
                choices=[dict(finish_reason=finish, message=dict(content=content, reasoning_content='thinking'))],
                usage=dict(prompt_tokens=100, completion_tokens=30), timings=dict(predicted_per_second=50.0))


def call(raw, model=client.MODEL, environ=None):
    tmp = tempfile.TemporaryDirectory()
    output = Path(tmp.name)/'request'
    with patch.dict(os.environ, environ or {}, clear=False), \
         patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(raw).encode())) as http:
        try:
            return client.request_model(MESSAGES, model, output), http, output, tmp
        except Exception as error:
            return error, http, output, tmp


class SelfHostedTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {client.URL_VARIABLE: ''})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_request_shape_has_pinned_options_and_no_credential(self):
        value, http, output, tmp = call(response('```json\n{"outcome":"no_change"}\n```'))
        self.addCleanup(tmp.cleanup)
        self.assertEqual(value, {'outcome': 'no_change'})
        request = http.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:8080/v1/chat/completions')
        self.assertIsNone(request.get_header('Authorization'))
        body = json.loads(request.data)
        self.assertEqual(body, dict(client.options_for(client.MODEL), model=client.MODEL, messages=MESSAGES, stream=False))
        self.assertEqual(body['chat_template_kwargs'], {'reasoning_effort': 'high'})
        self.assertEqual(body['temperature'], 1.0)
        record = json.loads((output/'request-measurement.json').read_text())
        self.assertEqual((record['backend'], record['status']), ('selfhosted', 'response_received'))
        self.assertEqual(record['system_fingerprint'], 'b1234-abc')
        self.assertTrue(record['json_fence_removed'])

    def test_only_loopback_tunnel_urls_are_accepted(self):
        for url in ('http://10.0.0.5:8080/v1/chat/completions', 'https://127.0.0.1:8080/v1/chat/completions',
                    'http://example.com/v1/chat/completions', 'http://127.0.0.1:8080/other'):
            with self.subTest(url=url), patch.dict(os.environ, {client.URL_VARIABLE: url}), \
                 patch.object(client.urllib.request, 'urlopen') as http:
                with self.assertRaises(client.ProviderError):
                    client.credential()
                with tempfile.TemporaryDirectory() as tmp, self.assertRaises(client.ProviderError):
                    client.request_model(MESSAGES, client.MODEL, Path(tmp)/'request')
                http.assert_not_called()
        with patch.dict(os.environ, {client.URL_VARIABLE: 'http://localhost:9000/v1/chat/completions'}):
            self.assertEqual(client.credential(), '')

    def test_identity_mismatch_and_truncation_are_failures(self):
        error, _, output, tmp = call(response(model='some-other-gguf'))
        self.addCleanup(tmp.cleanup)
        self.assertIsInstance(error, client.ProviderIdentityError)
        self.assertEqual(json.loads((output/'request-measurement.json').read_text())['failure_stage'], 'provider_identity_mismatch')
        error, _, output, tmp = call(response(finish='length'))
        self.addCleanup(tmp.cleanup)
        self.assertIsInstance(error, client.ProviderError)
        self.assertEqual(json.loads((output/'request-measurement.json').read_text())['failure_stage'], 'truncated_at_token_limit')

    def test_unlisted_model_is_refused_and_options_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(client.ProviderError):
            client.request_model(MESSAGES, 'inkling-2-mini-q2', Path(tmp)/'request')
        options = client.options_for(client.MODEL)
        options['chat_template_kwargs']['reasoning_effort'] = 'none'
        self.assertEqual(client.options_for(client.MODEL)['chat_template_kwargs'], {'reasoning_effort': 'high'})

    def test_live_suite_defaults_to_the_q8_model(self):
        parser_args = live_suite.argparse.Namespace(locked=False, backend='selfhosted', model=None, strategy='candidate_semantic_blocks')
        self.assertEqual(live_suite.resolve_configuration(parser_args)['model'], client.MODEL)


if __name__ == '__main__':
    unittest.main()
