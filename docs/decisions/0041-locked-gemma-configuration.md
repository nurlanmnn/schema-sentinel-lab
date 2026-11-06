# Decision 0041: lock Gemma 4 31B with semantic blocks 3.1

The user chose to stop comparing models on 5 November 2026. Subsequent live
evaluations use one frozen configuration:

| Setting | Value |
| --- | --- |
| Backend | NVIDIA direct hosted API |
| Model | `google/gemma-4-31b-it` |
| Strategy / prompt | `candidate_semantic_blocks`, prompt 3.1 |
| Sampling | temperature .5, top_p 1, seed 0, 4096 output tokens |
| Envelope | raw JSON or one complete outer json fence |

This was the best observed configuration: 6/8 validated on the eight
live-eligible authored migrations (decision 0038). Ultra/3.1 gave 5/8, Laguna
2/8, local Ministral 0/6, and DeepSeek was provider-unavailable (0039, 0040).
These cases informed prompt development, so 6/8 is a development result, not
held-out reliability.

Select it with `--locked`:

```sh
.venv/bin/python -m patchgen.live_suite --locked --full-benchmark --output patchgen/evidence/NEW-locked
```

`--locked` refuses `--backend`, `--model` or `--strategy` overrides, and the
summary records `locked_configuration: "0041"`. The CLI default remains the
local Ollama backend, so nothing calls a hosted provider unless selected. No
fallback is enabled; provider errors still stop as `provider_unavailable`.

Changing the model, prompt, sampling, or envelope parsing requires a new
decision. Prompt tuning must not be counted against the 6/8 baseline. The next
work is a bounded repair loop on this configuration, measured separately from
first-pass results (see `docs/patch-generation/repair-loop-plan.md`). Human
approval remains required for every patch.
