# AMD provider comparison

The optional `amd` backend permits only `Gemma-4-31B-IT` through
`https://api.tokenlab.amd.com/v1/chat/completions`. It reuses the locked NVIDIA
Gemma sampling options and JSON envelope parser so the provider comparison
keeps temperature 0.5, top_p 1, seed 0, and max_tokens 4096. Prompts and the
decision 0041 `--locked` NVIDIA route remain unchanged. AMD results are
reported separately with `backend: "amd"`; no live AMD result is claimed here.

Credentials are read at runtime from `AMD_API_KEY` or the owner-only
`~/.config/schema-sentinel/amd.key` file. Evidence excludes the authorization
header and redacts credential echoes from provider responses and errors.
The transport uses `/etc/ssl/cert.pem` when present and otherwise default TLS
roots. No new dependencies are required. Generated patches still require
validation and human approval.

Offline acceptance tests mock HTTP, credentials, and pipeline launches. They
cover request shape, locked options, redaction, infrastructure failures, CLI
selection, and zero-request harness failure accounting. To run the patchgen
tests without the full pipeline test that binds runtime ports 8000–8002:

```sh
SCHEMA_SENTINEL_SKIP_LOOPBACK=1 .venv/bin/python -m unittest discover -s patchgen/tests
```

Existing provider HTTP tests use synthetic credentials and ephemeral loopback
ports; they do not call live models.
