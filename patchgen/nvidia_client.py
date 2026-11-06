"""Explicit free Nemotron transport and local credential setup."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request

MODEL = 'nvidia/nemotron-3-ultra-550b-a55b'
MODELS = (MODEL, 'nvidia/nemotron-3.5-super-vl-120b-a12b', 'google/gemma-4-31b-it', 'poolside/laguna-xs-2.1')
API_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
KEY_FILE = Path.home() / '.config/schema-sentinel/nvidia.key'
OPTIONS = {
    'temperature': 1,
    'top_p': 0.95,
    'max_tokens': 4096,
    'chat_template_kwargs': {'enable_thinking': False},
}

# Shared failure types let the generator stop after an unavailable provider.
from patchgen.openrouter_client import ProviderError, ProviderHTTPError, ProviderIdentityError


def options_for(model):
    if model not in MODELS:
        raise ProviderError('Unsupported model')
    if model.startswith('google/'):
        return dict(temperature=0.5, top_p=1, seed=0, max_tokens=4096)
    if model == 'poolside/laguna-xs-2.1':
        return dict(temperature=1, top_p=0.95, max_tokens=4096)
    return dict(OPTIONS)


def parse_content(content):
    """Accept raw JSON or one complete JSON fence; never extract JSON from prose."""
    if not isinstance(content, str):
        raise ProviderError('Model content must be text')
    stripped = content.strip()
    normalized = False
    if stripped.startswith('```json\n') and stripped.endswith('\n```'):
        stripped = stripped[len('```json\n'):-len('\n```')]
        normalized = True
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ProviderError('Model response must be a JSON object')
    return value, normalized


def credential():
    token = os.environ.get('NVIDIA_API_KEY', '').strip()
    if not token and KEY_FILE.is_file():
        if KEY_FILE.stat().st_mode & 0o077:
            raise ProviderError('NVIDIA key file must be owner-only. Run chmod 600 on the key file.')
        token = KEY_FILE.read_text().strip()
    if not token or any(character.isspace() for character in token):
        raise ProviderError('Set NVIDIA_API_KEY or run python -m patchgen.nvidia_client setup-key.')
    return token


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def request_model(messages, model, output):
    if model not in MODELS:
        raise ProviderError('This transport permits only explicitly allowed NVIDIA Nemotron models.')
    token = credential()
    output.mkdir(parents=True, exist_ok=False)
    payload = json.loads(messages[-1]['content'])
    request = dict(options_for(model), model=model, messages=messages, stream=False)
    save(output / 'request.json', request)
    save(output / 'prompt.json', dict(version=payload['prompt_version'],
         sha256=hashlib.sha256(json.dumps(messages).encode()).hexdigest(), messages=messages))
    context = ssl.create_default_context()
    # macOS system roots also support Python installations without bundled certificates.
    system_roots = Path('/etc/ssl/cert.pem')
    if system_roots.is_file():
        context.load_verify_locations(str(system_roots))
    http_request = urllib.request.Request(
        API_URL, data=json.dumps(request).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
        method='POST',
    )
    started = time.monotonic()
    measurement = dict(backend='nvidia', status='request_started', model=model)
    try:
        with urllib.request.urlopen(http_request, timeout=600, context=context) as response:
            raw = json.load(response)
        # Credentials belong only in the HTTP header, including on malformed responses.
        raw = json.loads(json.dumps(raw).replace(token, '[REDACTED]'))
        if not isinstance(raw, dict):
            raise ProviderError('NVIDIA response must be a JSON object.')
        save(output / 'raw-response.json', raw)
        if raw.get('error'):
            raise ProviderError('NVIDIA returned an API error. See raw-response.json.')
        if raw.get('model', '').removesuffix(':free') != model.removesuffix(':free'):
            raise ProviderIdentityError('NVIDIA returned an unverified model identifier: ' + str(raw.get('model')))
        choices = raw.get('choices')
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get('finish_reason') != 'stop':
            raise ProviderError('Nemotron response was incomplete, refused, or truncated.')
        value, normalized = parse_content(choices[0]['message']['content'])
        measurement['json_fence_removed'] = normalized
        if not isinstance(value, dict):
            raise ProviderError('Nemotron response must be a JSON object.')
        measurement.update(status='response_received', provider=raw.get('provider'),
                           response_id=raw.get('id'), usage=raw.get('usage'))
        save(output / 'parsed-response.json', value)
        return value
    except ProviderIdentityError:
        measurement['status'] = 'provider_identity_mismatch'
        raise
    except urllib.error.HTTPError as error:
        measurement.update(status='http_error', http_status=error.code,
                           retry_after=error.headers.get('Retry-After'))
        message = error.read(65536).decode('utf8', errors='replace').replace(token, '[REDACTED]')
        try:
            details = json.loads(message)
            if isinstance(details, dict):
                details.pop('user_id', None)
            message = json.dumps(details)
        except ValueError:
            pass
        save(output / 'http-error.json', dict(status=error.code, body=message))
        raise ProviderHTTPError(f'NVIDIA HTTP {error.code}: {message[:1000]}') from None
    except (OSError, ValueError, KeyError, TypeError) as error:
        measurement['status'] = 'failed'
        raise ProviderError(str(error).replace(token, '[REDACTED]')) from None
    finally:
        measurement['elapsed_seconds'] = time.monotonic() - started
        save(output / 'request-measurement.json', measurement)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup-key', 'check-key'))
    args = parser.parse_args()
    try:
        if args.action == 'check-key':
            credential()
            print('NVIDIA credential is available locally.')
            return 0
        token = getpass.getpass('Paste the NVIDIA key (hidden): ').strip()
        if not token or any(character.isspace() for character in token):
            raise ProviderError('Key must be nonempty and contain no whitespace.')
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            output.write(token + '\n')
        print('Saved an owner-only key outside the repository.')
        return 0
    except (OSError, ValueError) as error:
        print(str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
