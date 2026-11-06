# Poolside Laguna XS 2.1: frozen coding-model trial

**Result: 2/8 patches validated (25%).** Keep Gemma 31B as the best observed configuration for these eight cases.

| Configuration | Validated patches | Model-request wall seconds |
|---|---:|---:|
| Gemma 31B / semantic blocks 3.1 | 6/8 | 824.83 |
| Ultra / semantic blocks 3.1 | 5/8 | 264.14 |
| Laguna XS 2.1 / semantic blocks 3.1 | 2/8 | 128.70 |

Laguna completed 24 actual benchmark requests, with no feedback/repair attempts or model fallback. One separate connectivity probe succeeded. All 24 request-message bodies and prompt hashes match the preceding Gemma trial exactly; see [prompt comparison](prompt-comparison.json). Source revisions, output token budget, JSON-envelope parsing, edit contracts, compilation checks and independent semantic oracles were unchanged.

Laguna uses NVIDIA-documented temperature 1/top_p .95 and a shared 4096 output-token budget. Gemma used temperature .5/top_p 1/seed 0. These compare configurations with one stochastic sample per case; no statistical model ranking or held-out reliability is established. Wall time includes free-provider queueing and different output lengths; it is not a controlled inference-speed result.

| Case | Outcome |
|---|---|
| pubsub-rename | Pass: compiled, tests and actual three-runtime pub/sub validated. |
| pubsub-removal | Rejected: Python before block did not contain complete source lines. |
| pubsub-utf8 | Rejected: TypeScript decoder received a string/Uint8Array union rather than preserving version-specific types. |
| telemetry-rename | Pass: compiled and independent runtime checks validated. |
| telemetry-precision | Rejected: Python response edits value was not an array. |
| telemetry-units | Rejected after compilation: C# observed 106.2 instead of the exact decoded float32 promoted to double, 106.19999694824219. Wire bytes and speeding decision at the first mismatch were correct; this was an exact observation failure, not incorrect unit arithmetic. |
| inventory-width | Rejected: Python included an unchanged edit. |
| telemetry-quantized | Rejected: C# and TypeScript included unchanged edits. |

Every passing patch remains a proposal requiring human approval. No generated patch was merged. These eight authored migrations are the eligible live route from the twenty-case deterministic suite; the other twelve cases are not counted as model successes. The prompt was developed on these cases, so this is development evidence, not unseen-case validation.

Verification: all 269 patch-generation tests passed, including an actual loopback HTTP check that Laguna sends its exact model identifier without Nemotron-only flags. Credentials remain outside the repository. Prompts, raw responses, resolutions, failures, timings and successful review bundles are retained.

Reproduction (choose a fresh output directory):

```sh
.venv/bin/python -m patchgen.live_suite --backend nvidia \
  --model poolside/laguna-xs-2.1 --strategy candidate_semantic_blocks \
  --full-benchmark --output patchgen/evidence/nvidia-laguna-xs21-002
```
