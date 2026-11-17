"""Synthetic transport responses only; no sockets, credentials or model API calls."""
import io
import json
from pathlib import Path
import ssl
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from patchgen import nvidia_client, openrouter_client, live_suite, fresh_attempts, fresh_manifest


class RequestFailureTests(unittest.TestCase):
    def test_cloud_measurements_and_collection_distinguish_transport_budget_and_model(self):
        for client in (nvidia_client, openrouter_client):
            def response(content='{}', finish='stop', **extra):
                return dict(model=client.MODEL, choices=[dict(finish_reason=finish, message=dict(content=content))], **extra)
            scenarios = [
                (TimeoutError('timed out'), 'request_timeout'),
                (urllib.error.URLError(TimeoutError('timed out')), 'request_timeout'),
                (urllib.error.URLError(ConnectionRefusedError('refused')), 'connection_error'),
                (urllib.error.URLError(ssl.SSLError('TLS failure')), 'tls_error'),
                (response('', 'length'), 'truncated_at_token_limit'),
                (response('  '), 'empty_provider_response'),
                (dict(model=client.MODEL, choices=[]), 'incomplete_provider_response'),
                (dict(error={'message':'unavailable'}), 'provider_response_error'),
                (b'', 'incomplete_provider_response'),
                (response('not JSON'), 'model_validation'),
            ]
            scenarios += [(urllib.error.HTTPError('https://synthetic.invalid', status, 'error', {}, io.BytesIO(b'{}')),
                           'provider_http_error') for status in (429, 500, 503)]
            for raw, stage in scenarios:
                with self.subTest(client=client.__name__, stage=stage), tempfile.TemporaryDirectory() as tmp:
                    target = Path(tmp)
                    request = target/'run/proposal/requests/01'
                    measurement = target/'run/report.json'
                    body = raw if isinstance(raw, bytes) else json.dumps(raw).encode() if isinstance(raw, dict) else None
                    with patch.object(client, 'credential', return_value='synthetic-key'), \
                         patch.object(client.urllib.request, 'urlopen', side_effect=raw if isinstance(raw, Exception) else None,
                                      return_value=io.BytesIO(body or b'')) as http:
                        with self.assertRaises(client.ProviderError):
                            client.request_model([dict(role='user', content='{"prompt_version":"test"}')], client.MODEL, request)
                        self.assertEqual(http.call_count, 1)
                    measurement.write_text(json.dumps(dict(status='failed', proposal_report=dict(mode='live_model', backend=client.__name__.split('.')[-1].removesuffix('_client')))))
                    row = live_suite.collect(target, 1, 1)
                    self.assertEqual(row['failure_stage'], stage)
                    self.assertEqual(row['failure_category'], 'model' if stage == 'model_validation' else 'model_budget' if stage == 'truncated_at_token_limit' else 'infrastructure')
                    self.assertFalse(row['generated_patch_validated'])

    def test_fresh_counts_keep_infrastructure_and_budget_in_denominator(self):
        outcomes = [dict(failure_category='infrastructure', infrastructure_failure=True, truncated_at_token_limit=False),
                    dict(failure_category='model_budget', infrastructure_failure=False, truncated_at_token_limit=True),
                    dict(failure_category='model', infrastructure_failure=False, truncated_at_token_limit=False),
                    {}, {}]
        rows = [dict(status='failed' if i < 3 else 'validation_passed', generated_patch_validated=i >= 3,
                     model_requests=1, generation_seconds=1, **outcome) for i, outcome in enumerate(outcomes)]
        with tempfile.TemporaryDirectory() as tmp, patch('builtins.print'), \
             patch.object(fresh_attempts, 'DEFAULT', Path(tmp)/'attempts.jsonl'), \
             patch.object(fresh_manifest, 'verify', return_value={}), \
             patch.object(Path, 'read_bytes', return_value=b'synthetic sealed inputs'), \
             patch.object(live_suite.subprocess, 'check_output', return_value='a'*40), \
             patch.object(live_suite.subprocess, 'run') as process, \
             patch.object(live_suite, 'collect', side_effect=rows):
            process.return_value.returncode = 1
            output = Path(tmp)/'out'
            self.assertEqual(live_suite.execute(output, 'ministral-3:8b', fresh=True, sample=1), 1)
            report = json.loads((output/'summary.json').read_text())
            self.assertEqual(report['validated_by_split']['fresh_screen'], '2/5')
            self.assertEqual(report['model_patch_validation_rate'], 2/5)
            self.assertEqual(report['infrastructure_failures'], 1)
            self.assertEqual(report['truncated_at_token_limit'], 1)
            self.assertEqual(report['model_failures'], 1)
            self.assertEqual(process.call_count, 5)
