"""Self-hosted OpenAI-compatible transport (llama.cpp or vLLM) reached only through a loopback tunnel.

The server runs on a rented GPU machine; an SSH tunnel exposes it on this computer's loopback address.
Requests never leave through any other route, so no API credential is used or stored.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from patchgen.nvidia_client import parse_content, save
from patchgen.openrouter_client import ProviderError, ProviderHTTPError, ProviderIdentityError
from patchgen.request_failures import response_stage, transport_stage

URL_VARIABLE = 'SCHEMA_SENTINEL_SELFHOSTED_URL'
DEFAULT_URL = 'http://127.0.0.1:8080/v1/chat/completions'
LOOPBACK_HOSTS = ('127.0.0.1', 'localhost', '::1')
# Served names are the server's --alias, one per GGUF file, so the weights in use are explicit.
# Sampling: the model's generation_config (temperature 1.0) and its chat template's default effort ("high"),
# pinned here so a template default change cannot silently alter a run. Output is capped because the
# model card warns of long reasoning loops.
INKLING_OPTIONS = {'temperature': 1.0, 'seed': 0, 'max_tokens': 16384,
                   'chat_template_kwargs': {'reasoning_effort': 'high'}}
SCREENING_OPTIONS = {
    'inkling-2-mini-q8_0': INKLING_OPTIONS,
    'inkling-2-mini-bf16': INKLING_OPTIONS,
}
MODELS = tuple(SCREENING_OPTIONS)
MODEL = MODELS[0]


def options_for(model):
    if model not in MODELS:
        raise ProviderError('Unsupported model')
    return json.loads(json.dumps(SCREENING_OPTIONS[model]))


def api_url():
    url = os.environ.get(URL_VARIABLE, '').strip() or DEFAULT_URL
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'http' or parts.hostname not in LOOPBACK_HOSTS or parts.path != '/v1/chat/completions':
        raise ProviderError(URL_VARIABLE + ' must be http://127.0.0.1:<port>/v1/chat/completions (an SSH tunnel).')
    return url


def credential():
    # No secret exists for this route; validating the loopback address is the precondition instead.
    api_url()
    return ''


def request_model(messages, model, output):
    if model not in MODELS:
        raise ProviderError('This transport permits only explicitly allowed self-hosted models.')
    url = api_url()
    output.mkdir(parents=True, exist_ok=False)
    payload = json.loads(messages[-1]['content'])
    request = dict(options_for(model), model=model, messages=messages, stream=False)
    save(output / 'request.json', request)
    save(output / 'prompt.json', dict(version=payload['prompt_version'],
         sha256=hashlib.sha256(json.dumps(messages).encode()).hexdigest(), messages=messages))
    http_request = urllib.request.Request(url, data=json.dumps(request).encode(),
                                          headers={'Content-Type': 'application/json'}, method='POST')
    started = time.monotonic()
    measurement = dict(backend='selfhosted', status='request_started', model=model)
    try:
        with urllib.request.urlopen(http_request, timeout=1800) as response:
            try:
                raw = json.load(response)
            except (ValueError, UnicodeError):
                measurement['failure_stage'] = 'incomplete_provider_response'
                raise
        stage = response_stage(raw)
        if stage:
            measurement['failure_stage'] = stage
        if not isinstance(raw, dict):
            raise ProviderError('Self-hosted response must be a JSON object.')
        save(output / 'raw-response.json', raw)
        if raw.get('error'):
            raise ProviderError('Self-hosted server returned an API error. See raw-response.json.')
        if raw.get('model') != model:
            raise ProviderIdentityError('Self-hosted server returned an unverified model identifier: ' + str(raw.get('model')))
        choices = raw.get('choices')
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get('finish_reason') != 'stop':
            raise ProviderError('Self-hosted response was incomplete, refused, or truncated.')
        value, normalized = parse_content(choices[0]['message']['content'])
        measurement['json_fence_removed'] = normalized
        if not isinstance(value, dict):
            raise ProviderError('Self-hosted response must be a JSON object.')
        measurement.update(status='response_received', provider='selfhosted',
                           system_fingerprint=raw.get('system_fingerprint'),
                           response_id=raw.get('id'), usage=raw.get('usage'), timings=raw.get('timings'))
        save(output / 'parsed-response.json', value)
        return value
    except ProviderIdentityError:
        measurement.update(status='provider_identity_mismatch', failure_stage='provider_identity_mismatch')
        raise
    except urllib.error.HTTPError as error:
        measurement.update(status='http_error', failure_stage='provider_http_error', http_status=error.code,
                           retry_after=error.headers.get('Retry-After'))
        message = error.read(65536).decode('utf8', errors='replace')
        save(output / 'http-error.json', dict(status=error.code, body=message))
        raise ProviderHTTPError(f'Self-hosted HTTP {error.code}: {message[:1000]}') from None
    except (OSError, ValueError, KeyError, TypeError) as error:
        measurement['status'] = 'failed'
        stage = transport_stage(error)
        if stage:
            measurement['failure_stage'] = stage
        raise ProviderError(str(error)) from None
    finally:
        measurement['elapsed_seconds'] = time.monotonic() - started
        save(output / 'request-measurement.json', measurement)
