"""AMD-hosted Gemma transport using the locked NVIDIA Gemma sampling options."""
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request

from patchgen.nvidia_client import options_for as nvidia_options_for, parse_content, save
from patchgen.openrouter_client import ProviderError, ProviderHTTPError, ProviderIdentityError
from patchgen.request_failures import response_stage, transport_stage

MODEL = 'Gemma-4-31B-IT'
MODELS = (MODEL,)
API_URL = 'https://api.tokenlab.amd.com/v1/chat/completions'
KEY_FILE = Path.home() / '.config/schema-sentinel/amd.key'


def options_for(model):
    if model not in MODELS:
        raise ProviderError('Unsupported model')
    return nvidia_options_for('google/gemma-4-31b-it')


def credential():
    token = os.environ.get('AMD_API_KEY', '').strip()
    if not token and KEY_FILE.is_file():
        if KEY_FILE.stat().st_mode & 0o077:
            raise ProviderError('AMD key file must be owner-only. Run chmod 600 on the key file.')
        token = KEY_FILE.read_text().strip()
    if not token or any(character.isspace() for character in token):
        raise ProviderError('Set AMD_API_KEY or provide an owner-only ~/.config/schema-sentinel/amd.key file.')
    return token


def request_model(messages, model, output):
    if model not in MODELS:
        raise ProviderError('This transport permits only explicitly allowed AMD models.')
    token = credential()
    output.mkdir(parents=True, exist_ok=False)
    payload = json.loads(messages[-1]['content'])
    request = dict(options_for(model), model=model, messages=messages, stream=False)
    save(output / 'request.json', request)
    save(output / 'prompt.json', dict(version=payload['prompt_version'],
         sha256=hashlib.sha256(json.dumps(messages).encode()).hexdigest(), messages=messages))
    # Prefer the macOS system roots when this Python lacks working bundled certificates.
    system_roots = Path('/etc/ssl/cert.pem')
    context = ssl.create_default_context(cafile=str(system_roots)) if system_roots.is_file() else ssl.create_default_context()
    http_request = urllib.request.Request(
        API_URL, data=json.dumps(request).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
        method='POST',
    )
    started = time.monotonic()
    measurement = dict(backend='amd', status='request_started', model=model)
    try:
        with urllib.request.urlopen(http_request, timeout=600, context=context) as response:
            try:
                raw = json.load(response)
            except (ValueError, UnicodeError):
                measurement['failure_stage'] = 'incomplete_provider_response'
                raise
        # Credentials belong only in the HTTP header, including on malformed responses.
        raw = json.loads(json.dumps(raw).replace(token, '[REDACTED]'))
        stage = response_stage(raw)
        if stage:
            measurement['failure_stage'] = stage
        if not isinstance(raw, dict):
            raise ProviderError('AMD response must be a JSON object.')
        save(output / 'raw-response.json', raw)
        if raw.get('error'):
            raise ProviderError('AMD returned an API error. See raw-response.json.')
        if raw.get('model', '').removesuffix(':free') != model.removesuffix(':free'):
            raise ProviderIdentityError('AMD returned an unverified model identifier: ' + str(raw.get('model')))
        choices = raw.get('choices')
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get('finish_reason') != 'stop':
            raise ProviderError('AMD response was incomplete, refused, or truncated.')
        value, normalized = parse_content(choices[0]['message']['content'])
        measurement['json_fence_removed'] = normalized
        if not isinstance(value, dict):
            raise ProviderError('AMD response must be a JSON object.')
        measurement.update(status='response_received', provider=raw.get('provider'),
                           response_id=raw.get('id'), usage=raw.get('usage'))
        save(output / 'parsed-response.json', value)
        return value
    except ProviderIdentityError:
        measurement.update(status='provider_identity_mismatch', failure_stage='provider_identity_mismatch')
        raise
    except urllib.error.HTTPError as error:
        measurement.update(status='http_error', failure_stage='provider_http_error', http_status=error.code,
                           retry_after=error.headers.get('Retry-After', '').replace(token, '[REDACTED]') or None)
        message = error.read(65536).decode('utf8', errors='replace').replace(token, '[REDACTED]')
        try:
            details = json.loads(message)
            if isinstance(details, dict):
                details.pop('user_id', None)
            message = json.dumps(details)
        except ValueError:
            pass
        save(output / 'http-error.json', dict(status=error.code, body=message))
        raise ProviderHTTPError(f'AMD HTTP {error.code}: {message[:1000]}') from None
    except (OSError, ValueError, KeyError, TypeError) as error:
        measurement['status'] = 'failed'
        stage = transport_stage(error)
        if stage:
            measurement['failure_stage'] = stage
        raise ProviderError(str(error).replace(token, '[REDACTED]')) from None
    finally:
        measurement['elapsed_seconds'] = time.monotonic() - started
        save(output / 'request-measurement.json', measurement)

