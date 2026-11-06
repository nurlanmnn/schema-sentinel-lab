# NVIDIA model and prompt evaluation

Public synthetic development benchmark; no generated patch was merged. Every passing patch still requires human approval.

## Results

| Configuration | Validated patches |
|---|---|
| Ultra / original 2.5 | 2/8 |
| Ultra / semantic 3.0 | 4/8 |
| Ultra / semantic blocks 3.1 | 5/8 |
| Gemma / semantic blocks 3.1 | 6/8 |
| Laguna XS 2.1 / semantic blocks 3.1 | 2/8 |

| Case | Ultra / original 2.5 | Ultra / semantic 3.0 | Ultra / semantic blocks 3.1 | Gemma / semantic blocks 3.1 |
|---|---|---|---|---|
| pubsub-rename | pass | pass | pass | pass |
| pubsub-removal | rejected | pass | pass | pass |
| pubsub-utf8 | rejected | rejected | rejected | rejected |
| telemetry-rename | pass | pass | pass | pass |
| telemetry-precision | rejected | pass | pass | pass |
| telemetry-units | rejected | rejected | pass | pass |
| inventory-width | rejected | rejected | rejected | rejected |
| telemetry-quantized | rejected | rejected | rejected | pass |

## Serving measurements

| Configuration | Requests in scored case attempts | Model-request wall seconds |
|---|---:|---:|
| Ultra / original 2.5 | 24 | 197.57 |
| Ultra / semantic 3.0 | 24 | 249.10 |
| Ultra / semantic blocks 3.1 | 24 | 264.14 |
| Gemma / semantic blocks 3.1 | 24 | 824.83 |

Serving time is separate from prepared-fixture workflow time and human review. Provider failures, interrupted configurations, and the connectivity probe are retained separately; this table is not total account usage.

## Interpretation

The original and semantic-line prompts used the same Ultra model and sampling settings. The block follow-up changes both prompt guidance and edit representation. These are one stochastic sample per case/configuration; prompt development used these cases and prior failures. The observed improvement is not a statistically isolated prompt effect or evidence of unseen-case reliability.

The units migration now passes exact float32 observations across Python, TypeScript and C#. The semantic guidance explicitly widens decoded C# float values to double before JSON serialization and checks producers, wire representation, observations and predicates. No expected numeric answer or reference patch is supplied in prompts.

Ultra block failures: the bytes patch failed TypeScript compilation after applying decoding to a version-dependent string/bytes union; integer-width returned an inconsistent empty patch/no-change outcome; quantization remained rejected. Full diagnostics and raw outputs are retained.

Super 3.5 was requested but NVIDIA returned private/nvidia/nemotron-3.5-super-120b-a12b rather than the requested nvidia/nemotron-3.5-super-vl-120b-a12b. No documented identity mapping was verified. These calls are unscored, and the comparison was interrupted. Historical failed labels in that old cohort are superseded by super35-interpretation.json. New code stops immediately and reports provider_unavailable on an identity mismatch.

An HTTP 502 interrupted the Ultra block cohort on integer-width. Only integer-width and quantization were retried in a separate fresh output directory, once. The table merges the six completed first-cohort cases with those two fresh attempts; it does not describe an uninterrupted 8/8-available run. This was a provider retry, not feedback repair of a generated patch.

The initial Gemma benchmark was interrupted because responses used a Markdown JSON fence. The final cohort accepts raw JSON or a single complete outer json fence, preserving the original response and recording normalization. Extra prose, invalid JSON, and invalid edits remain rejected. The final comparison therefore also differs in transport envelope support; it does not count interrupted strict-envelope attempts as patch-quality evidence.

Gemma uses NVIDIA-documented temperature .5/top_p 1/seed 0; Ultra uses temperature 1/top_p .95. Both have 4096 output tokens; Ultra thinking is disabled. These are model/configuration comparisons, not a parameter-size experiment.

Only eight of the twenty authored deterministic migrations are eligible for this live route. The other twelve are schema-only or require pinned policy. This is not a twenty-case live-model result. The human baseline remains deferred.

## Evidence

- [Original and semantic line comparison](../nvidia-model-prompt-comparison-001/comparison.json)
- [Super identity interpretation](../nvidia-model-prompt-comparison-001/super35-interpretation.json)
- [Ultra semantic blocks](../nvidia-block-model-comparison-001/ultra-semantic-blocks/summary.json)
- [Ultra provider retry and final cases](../nvidia-block-ultra-tail-001/summary.json)
- [Gemma semantic blocks with bounded JSON envelope parsing](../nvidia-block-gemma-envelope-001/summary.json)
- [Successful units review](../nvidia-block-model-comparison-001/ultra-semantic-blocks/telemetry-units/review/index.html)

Verification: 269 patch-generation tests passed. Transport tests use synthetic loopback HTTP responses and are separate from these actual model calls.

## Recommendation and remaining failures

Use Google Gemma 31B through NVIDIA with `candidate_semantic_blocks` for the next
accuracy-focused evaluation: it had the best observed result, 6/8. Ultra with the
same strategy achieved 5/8 with about one third of Gemma's total model-request
wall time in this sample. Free-provider queueing is included in that time; it is
not a controlled inference-speed benchmark. No automatic fallback is enabled.

Gemma's bytes patch failed C# compilation because it passed a Protobuf ByteString
to an API requiring byte[]. Its integer-width TypeScript response contained extra
text after the JSON and was rejected. Those failures remain visible; no repair
call or manual patch was counted as a success.

Recommended explicit command (use a fresh output path):

```sh
.venv/bin/python -m patchgen.live_suite --backend nvidia \
  --model google/gemma-4-31b-it --strategy candidate_semantic_blocks \
  --full-benchmark --output patchgen/evidence/nvidia-gemma-next-001
```

The existing CLI defaults remain unchanged. Before making broader sponsor
reliability claims, freeze the chosen configuration and evaluate new migrations
that were not used to develop these prompts. This experiment set is complete;
no additional model or prompt variants are running.


## Subsequent coding-specialist trial

Poolside Laguna XS 2.1 completed the same eight cases with 24 identical prompt-message bodies and no repairs: **2/8 validated**, in 128.70 seconds of total model-request wall time. It passed the two renames. Gemma remains the best observed configuration. See [Laguna results](../nvidia-laguna-xs21-001/summary.md) and decision 0039. All 269 patch-generation tests pass. These remain one-sample development results.
