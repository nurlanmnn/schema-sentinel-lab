# Free Gemma trial through OpenRouter

This opt-in backend uses `google/gemma-4-31b-it:free` through Google AI Studio.
The request selects that provider and disables provider fallback. It sends the
schema-change task and pinned runtime source excerpts for the selected case.

The first trial uses telemetry rename, which makes three requests. It uses the
existing candidate-edits prompt, temperature 0, seed 42, an 8192-token response
budget, JSON object mode and enabled reasoning. OpenRouter does not enforce
the full response schema for this endpoint. The host still checks edit ranges,
candidate reviews, source identity, compilation and independent runtime evidence.
These serving settings differ from the local Ollama structured-output run.

## Set up the credential

Create an account and API key at
[OpenRouter](https://openrouter.ai/settings/keys). In a Terminal at the Lab root:

```sh
.venv/bin/python -m patchgen.openrouter_client setup-key
```

The prompt hides the key and writes an owner-only file at
`~/.config/schema-sentinel/openrouter.key`. Existing files are preserved.
The backend also accepts `OPENROUTER_API_KEY` from the environment.

Verify local credential availability:

```sh
.venv/bin/python -m patchgen.openrouter_client check-key
```

This check reads the local credential only. Authentication is verified by the
first live request.

## Run the initial trial

```sh
.venv/bin/python -m patchgen.live_suite --backend openrouter \
  --case telemetry-rename --output /tmp/schema-sentinel-gemma-trial-001
```

Use a new output directory for each attempt. Read `summary.json` for the outcome,
request counts, latency and provider usage. Candidate or runtime failures remain
failed outcomes. A validated proposal gets a portable review bundle.

The eight-case comparison uses:

```sh
.venv/bin/python -m patchgen.live_suite --backend openrouter \
  --full-benchmark --output /tmp/schema-sentinel-gemma-eight-001
```

Free-tier quota and capacity can interrupt a run. HTTP errors retain their status
and any Retry-After header. Each file makes one request, without automatic retry.
Key values and authentication headers are excluded from saved request evidence.

## Verification before live use

Local HTTP tests exercise successful JSON responses, 401 and 429 responses,
truncation, invalid output, model substitution and rejection by the host edit
validator. These checks establish adapter behavior. A real Gemma result requires
the live request and its complete validation evidence.

Sources are the [OpenRouter authentication guide](https://openrouter.ai/docs/api-reference/authentication)
and the [Gemma endpoint listing](https://openrouter.ai/google/gemma-4-31b-it:free).
