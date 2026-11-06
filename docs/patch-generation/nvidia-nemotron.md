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

## Identity failure and follow-up

The first Super 3.5 evaluation returned the model identifier
`private/nvidia/nemotron-3.5-super-120b-a12b` for requests to
`nvidia/nemotron-3.5-super-vl-120b-a12b`. No authoritative alias mapping was
verified. Those responses are rejected as provider identity failures and do not
establish a model patch-validation rate. The interrupted comparison remains in
`nvidia-model-prompt-comparison-001`; its Super per-case historical `failed`
labels predate the corrected unavailable classification and must not be used as
model-quality scores. The new adapter and runner stop on the first such failure.

Google's `google/gemma-4-31b-it` is also explicitly allowed through the same
NVIDIA endpoint. Its connectivity probe succeeded. NVIDIA's own sample uses
model-specific temperature .5, top_p 1, seed 0; the adapter uses these with the
same 4096 output-token budget and no Nemotron-only chat-template options.
https://build.nvidia.com/google/gemma-4-31b-it

`candidate_semantic_blocks` version `3.1-semantic-blocks` combines general
semantic guidance with exact source blocks and explicit omission of unchanged
edits. It retains the original block resolver, candidate coverage, required
reference constraints, answer exclusion, compilation and runtime oracles.
It was developed after inspecting the first comparison, so it is a development
follow-up rather than held-out validation.

```sh
.venv/bin/python -m patchgen.nvidia_comparison \
  --model nvidia/nemotron-3-ultra-550b-a55b \
  --model google/gemma-4-31b-it \
  --strategy candidate_semantic_blocks \
  --output patchgen/evidence/nvidia-block-model-comparison-001
```

This final follow-up has two cohorts and sixteen case attempts, no automatic
repairs. Model comparison includes different provider-recommended sampling
options, so any outcome difference is between configurations, not parameter
count alone. No Chinese-developed model is added to the allowlist.

### Bounded JSON envelope support

Gemma's first benchmark requests returned a single Markdown `json` fence around
otherwise JSON-formatted content. The strict-envelope cohort was stopped and
retained separately at `nvidia-block-gemma-001`; it is incomplete and not a model
quality comparison. The transport now accepts raw JSON or exactly one complete
outer `json` fence, stripping only that wrapper. It never extracts JSON from prose,
accepts trailing text, repairs JSON, or changes edits. Raw content is retained and
`json_fence_removed` is recorded per request. Host edit, compilation and semantic
gates remain unchanged. A fresh final eight-case cohort is recorded separately at
`nvidia-block-gemma-envelope-001`. The adapter and sampling configuration are part
of the evaluated configuration; this is not a controlled prompt-only comparison.

## Poolside Laguna XS 2.1 coding-model trial

The explicit allowlist includes `poolside/laguna-xs-2.1`, a coding-focused model
at https://build.nvidia.com/poolside/laguna-xs-2.1. Its connectivity probe succeeded
with the exact requested model identity. Use temperature 1, top_p .95, max_tokens
4096, with no Nemotron-specific chat-template flags. No new API key is required.

```sh
.venv/bin/python -m patchgen.live_suite --backend nvidia \
  --model poolside/laguna-xs-2.1 --strategy candidate_semantic_blocks \
  --full-benchmark --output patchgen/evidence/nvidia-laguna-xs21-001
```

This is a single frozen-prompt eight-case development trial with unchanged
validation gates and no model repairs. See decision 0039 for the comparison limits.
