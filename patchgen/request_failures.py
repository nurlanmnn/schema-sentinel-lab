"""Failure labels only: transports retain their existing exception and retry behavior."""
import ssl
import urllib.error

INFRASTRUCTURE_STAGES = frozenset((
    'request_timeout', 'connection_error', 'tls_error', 'provider_http_error',
    'provider_identity_mismatch', 'provider_response_error', 'empty_provider_response',
    'incomplete_provider_response',
))


def transport_stage(error):
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, (TimeoutError,)):
        return 'request_timeout'
    if isinstance(reason, ssl.SSLError):
        return 'tls_error'
    if isinstance(error, OSError):
        return 'connection_error'
    return None


def response_stage(raw):
    if not isinstance(raw, dict):
        return 'incomplete_provider_response'
    choices = raw.get('choices')
    if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
        choice = choices[0]
        if choice.get('finish_reason') == 'length':
            return 'truncated_at_token_limit'
        content = choice.get('message', {}).get('content') if isinstance(choice.get('message'), dict) else None
        if content is None or (isinstance(content, str) and not content.strip()):
            return 'empty_provider_response'
        if choice.get('finish_reason') is None:
            return 'incomplete_provider_response'
    if raw.get('error'):
        return 'provider_response_error'
    if 'choices' in raw:
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            return 'incomplete_provider_response'
        return None
    # Ollama's response envelope.
    if raw.get('done_reason') == 'length':
        return 'truncated_at_token_limit'
    if not raw.get('done'):
        return 'incomplete_provider_response'
    content = raw.get('message', {}).get('content') if isinstance(raw.get('message'), dict) else None
    if content is None or (isinstance(content, str) and not content.strip()):
        return 'empty_provider_response'
    return None


def request_stage(measurement, raw=None):
    if measurement.get('failure_stage'):
        return measurement['failure_stage']
    if measurement.get('http_status'):
        return 'provider_http_error'
    if measurement.get('status') == 'provider_identity_mismatch':
        return 'provider_identity_mismatch'
    return response_stage(raw) if raw is not None else None
