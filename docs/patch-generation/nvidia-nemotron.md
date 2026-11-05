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

## Bounded model and prompt comparison

The explicit model allowlist also includes
`nvidia/nemotron-3.5-super-vl-120b-a12b`, whose direct free endpoint was verified
on NVIDIA Build on 2026-11-05:
https://build.nvidia.com/nvidia/nemotron-3.5-super-vl-120b-a12b
Neither model routes to another model or provider on failure.

`candidate_semantic_edits` is prompt version `3.0-semantic`, with the same edit
schema, reference-answer exclusion, and validation gates as `candidate_edits`
version 2.5. It adds general input/wire/decoded-observation consistency guidance,
including explicit C# widening when exact decoded float32 JSON values are required.
It includes no numeric benchmark answers. This is a development prompt informed
by previous failures, not a prompt selected using a held-out test set.

Run the finite comparison with:

```sh
.venv/bin/python -m patchgen.nvidia_comparison \
  --output patchgen/evidence/nvidia-model-prompt-comparison-001
```

This executes each model with each prompt on eight eligible migrations, one
sample per cell, sequentially. It stops after four cohorts or on unavailable
provider/runner state. Temperature, token budget, disabled thinking, edit contract,
fixture revisions, and runtime oracles are held fixed. There are no repair calls.
Single stochastic samples cannot establish statistical reliability or isolate a
prompt effect from sampling noise; repeatability requires a separate evaluation.
The other twelve deterministic benchmark cases remain explicitly ineligible for
this live route and are not counted as model successes.
