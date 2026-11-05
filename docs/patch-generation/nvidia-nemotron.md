# NVIDIA Nemotron evaluation

Explicit opt-in backend: `nvidia`, fixed model
`nvidia/nemotron-3-ultra-550b-a55b`, direct NVIDIA endpoint
`https://integrate.api.nvidia.com/v1/chat/completions`. No provider or model
fallback, automatic retries, or repair loop. Public synthetic testbed inputs only.

The NVIDIA Build page lists a free prototype endpoint as of 2026-11-05;
account allowance and serving availability must be checked through a real trial.
https://build.nvidia.com/nvidia/nemotron-3-ultra-550b-a55b

Save the key privately with `.venv/bin/python -m patchgen.nvidia_client setup-key`.
It uses a hidden terminal prompt and an exclusive owner-only file at
`~/.config/schema-sentinel/nvidia.key`, outside the repository. Alternatively set
`NVIDIA_API_KEY`. Never place credentials in prompts, evidence, or commits.

Initial requests use temperature 1, top_p .95, 4096 output tokens and thinking
disabled. No provider JSON constraint is assumed: the host rejects invalid JSON,
truncation, wrong model, invalid edit contracts, and failed runtime validation.
Transport source, request options, responses, timing, and token usage are retained
in evidence. Human approval remains required for every validated proposal.

Initial bounded trial:

```sh
.venv/bin/python -m patchgen.live_suite --backend nvidia \
  --case pubsub-rename --case telemetry-units \
  --output patchgen/evidence/nvidia-nemotron-initial-001
```

No live NVIDIA result is established by the integration's synthetic HTTP tests.
