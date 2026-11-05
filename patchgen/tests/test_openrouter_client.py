"""Exercise real HTTP serialization, failure retention, and the existing edit gate."""
from contextlib import contextmanager
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from patchgen import openrouter_client as client
from patchgen.generator import ContractError, generate

ROOT = Path(__file__).resolve().parents[2]
CASE = json.loads((ROOT/'patchgen/fixtures/entity-name-removal/input.json').read_text())
TOKEN = 'test-openrouter-secret'


@contextmanager
def service(status=200, raw=None):
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(dict(path=self.path, authorization=self.headers.get('Authorization'),
                                 body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Retry-After', '60')
            self.end_headers()
            self.wfile.write(json.dumps(raw).encode())
        def log_message(self, *args):
            pass
    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with patch.object(client, 'API_URL', f'http://127.0.0.1:{server.server_port}/chat/completions'),                  patch.dict('os.environ', {'OPENROUTER_API_KEY': TOKEN}):
                yield received
        finally:
            server.shutdown()
            worker.join()


def response(content, *, model=client.MODEL.removesuffix(':free'), finish='stop'):
    return dict(id='synthetic-http-response', model=model, provider='Google AI Studio',
                choices=[dict(finish_reason=finish, message=dict(content=content))],
                usage=dict(prompt_tokens=100, completion_tokens=30))


class OpenRouterTests(unittest.TestCase):
    def test_success_uses_free_model_and_keeps_key_out_of_evidence(self):
        messages = [dict(role='user', content=json.dumps(dict(prompt_version='test', response_schema={})))]
        with tempfile.TemporaryDirectory() as temporary, service(raw=response('{"outcome":"no_change"}')) as calls:
            output = Path(temporary)/'request'
            self.assertEqual(client.request_model(messages, client.MODEL, output), {'outcome': 'no_change'})
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]['authorization'], 'Bearer ' + TOKEN)
            body = calls[0]['body']
            self.assertEqual(body['model'], client.MODEL)
            self.assertFalse(body['provider']['allow_fallbacks'])
            self.assertEqual(body['provider']['only'], ['Google AI Studio'])
            self.assertEqual(body['response_format'], {'type': 'json_object'})
            for path in output.iterdir():
                self.assertNotIn(TOKEN, path.read_text())
            record = json.loads((output/'request-measurement.json').read_text())
            self.assertEqual(record['usage']['prompt_tokens'], 100)

    def test_authentication_and_rate_limit_errors_make_one_attempt(self):
        for status in (401, 429):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary,                  service(status=status, raw={'error': TOKEN}) as calls:
                output = Path(temporary)/'request'
                with self.assertRaisesRegex(client.ProviderError, f'HTTP {status}'):
                    client.request_model([dict(role='user', content='{"prompt_version":"test"}')],
                                         client.MODEL, output)
                self.assertEqual(len(calls), 1)
                record = json.loads((output/'request-measurement.json').read_text())
                self.assertEqual(record['http_status'], status)
                self.assertEqual(record['retry_after'], '60')
                self.assertNotIn(TOKEN, json.dumps(record))

    def test_invalid_truncated_and_substituted_responses_are_rejected(self):
        for raw in (response('not JSON'), response('{}', finish='length'), response('{}', model='other')):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as temporary, service(raw=raw):
                with self.assertRaises(client.ProviderError):
                    client.request_model([dict(role='user', content='{"prompt_version":"test"}')],
                                         client.MODEL, Path(temporary)/'request')

    def test_unapproved_model_stops_before_http(self):
        with tempfile.TemporaryDirectory() as temporary, service(raw=response('{}')) as calls:
            with self.assertRaisesRegex(client.ProviderError, 'only'):
                client.request_model([], 'paid/model', Path(temporary)/'request')
            self.assertEqual(calls, [])

    def test_cloud_output_still_passes_through_host_edit_validation(self):
        case = copy.deepcopy(CASE)
        case['affected_files'] = case['affected_files'][:1]
        invalid_edit = dict(outcome='patch', confidence=.5, rationale='Synthetic invalid edit',
                            assumptions=[], candidate_reviews=[],
                            edits=[dict(start_line=999999, end_line=999999, replacement_lines=['bad'])])
        with tempfile.TemporaryDirectory() as temporary, service(raw=response(json.dumps(invalid_edit))) as calls:
            with self.assertRaisesRegex(ContractError, 'file proposal rejected'):
                generate(case, client.MODEL, 'unused', Path(temporary), 'candidate_edits', backend='openrouter')
            self.assertEqual(len(calls), 1)
            evidence = json.loads((Path(temporary)/'requests/01/edit-validation.json').read_text())
            self.assertEqual(evidence['status'], 'failed')
