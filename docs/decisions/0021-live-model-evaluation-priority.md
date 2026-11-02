# 0021: Live model evaluation before more deterministic expansion

The user explicitly prioritized actual LLM patch generation and model choice.
Finish the inventory checkpoint already in flight, then stop expanding deterministic
policies until a live baseline is measured. Seven deterministic migrations and
known-answer replays are not evidence of model success.

## Baseline protocol

`patchgen.live_suite` runs the six previously validated migrations (Entity
rename/removal/UTF-8 on pub/sub and telemetry rename/precision/units) sequentially
through the independent detector, syntax locator, adapter and live generator.
Inventory is excluded from this first comparison. Use the installed local
Ministral 3 8B model with the existing candidate-edits prompt 2.5, fixed seed 42,
temperature zero, 16K context and 8192-token output bound. There is one request per
runtime file, no validation feedback or repair attempt, no reference response,
and no deterministic generation fallback. Compilation, original relay tests,
independent semantic/wire oracle and portable human review use the same gates as
the deterministic runs. Each case stays in the six-case validation denominator.

Retain raw requests/responses, exact model digest and serving metadata, prompt
hashes, per-file contract results, actual request count, generation wall time,
Ollama token/duration counters and allocation samples. Model allocation sampling
is not whole-system peak memory. Prepared pipeline timing is separate from
request generation and does not measure operational propagation or human time.
Failures to obey the edit contract, compilation failures and semantic failures
must be distinguished; do not label a contract rejection a runtime validation
success. Partial runs retain `running` and have no final rate.

Command on the prepared host (no download):

```sh
.venv/bin/python -m patchgen.live_suite --model ministral-3:8b --output patchgen/evidence/NEW-live
```

## Model reassessment

Observed host memory: 16 GiB. Installed non-Chinese local models include Ministral
3 3B and 8B; Qwen is excluded by the existing user constraint. Ollama reports the
8B model's 16K-context allocation as approximately 7.4 GB, fully GPU-resident at
baseline start. This is not a peak-memory guarantee.

Ministral 3 14B is a plausible stronger local candidate from the same family,
not an established solution. [Mistral's model documentation](https://docs.mistral.ai/models/ministral-3-14b-25-12)
identifies the 14B model and Apache-2.0 license. The [official Ollama package](https://ollama.com/library/ministral-3:14b)
listed on November 2, 2026 is Q4_K_M, 13.9B, 9.1 GB, digest prefix
4760c35aeb9d. Those are package properties, not measured memory or validation
performance on this Mac. Model/context allocation plus OS/application memory may
be tight on a 16 GiB shared-memory machine. Do not download it or start paid
inference under this reassessment alone. First inspect the 8B failure patterns.
If a larger comparison is authorized, use exact model digests and identical six
inputs, prompt, options, validator and no-repair policy. Report cold/warm loading
and generation timing separately when available. The already installed 3B offers
a smaller baseline without download, but it is not a stronger-model comparison.

No generated patch is merged or human-approved by this evaluation.
