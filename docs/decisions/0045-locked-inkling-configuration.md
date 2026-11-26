# Decision 0045: lock Inkling 2 Mini, self-hosted, with semantic blocks 3.1

Status: accepted by the user on 2026-11-25. This replaces the 0041 configuration.
Prompts, envelope parsing and the 0044 resolver rule are unchanged.

## Why 0041 had to change

NVIDIA retired `google/gemma-4-31b-it` on 2026-11-24 (HTTP 410, "end of life").
The only other host we used, AMD TokenLab, returned HTTP 503 on every fresh-screen
attempt on 2026-11-25. The 0041 configuration can no longer be run as written.
Real STE data is CUI, so the deliverable needs a model the sponsor can host
anyway. The sponsor proposal's fallback is a 14B–32B open model on one workstation
GPU.

## The new configuration

| Setting | Value |
| --- | --- |
| Backend | `selfhosted` (llama.cpp OpenAI-compatible server, reached on loopback) |
| Model | Inkling 2 Mini (Thinking Machines, US, Apache 2.0), 26B total / 3.4B active |
| Weights | `ggml-org/Inkling-2-Mini-GGUF`, `Inkling-2-Mini-Q8_0.gguf`, sha256 `652b8594…5274a` |
| Served name | `inkling-2-mini-q8_0` |
| Strategy / prompt | `candidate_semantic_blocks`, prompt 3.1 |
| Sampling | temperature 1.0, seed 0, 16384 output tokens, `reasoning_effort` "high" |
| Envelope | raw JSON or one complete outer json fence (unchanged) |
| Server | llama.cpp ROCm build b12723, `-ngl 999 --jinja`, at least 32768 context per concurrent request |

Setup steps: `docs/patch-generation/selfhosted-amd-inkling.md`. The 8-bit file is
28 GB, so it fits a 32 GB workstation GPU. Measured: about 33 GB of GPU memory and
2–3 minutes per request on one AMD MI300X.

## Evidence (all screening, none held-out)

| Set | Inkling 2 Mini (rule 0044) | Gemma 4 31B |
| --- | --- | --- |
| 8 development cases | 8/8 first pass | 6/8 under 0041 (0038) |
| 15 fresh-screen attempts | 11/15 | 9/15 sealed before 0044; 12/15 post-hoc counterfactual |

Details: `docs/patch-generation/model-screening-plan.md` (second extra run).

## Why Inkling and not self-hosted Gemma

Gemma would probably match Inkling on these cases: its post-hoc 12/15 against
Inkling's measured 11/15 is not a meaningful difference, and Gemma could not be
re-run under the same code. Inkling was chosen for reasons other than score:

- License: Apache 2.0, which suits an Apache 2.0 or MIT deliverable. Gemma has its own terms of use.
- Size: 28 GB against about 33 GB at 8-bit, with less active compute per token.
- Longevity: Inkling 2 Mini was released on 2026-11-20; Gemma 4 is already being retired by hosts.
- Origin: US developer. Chinese-origin models remain excluded (decisions 0002 and 0021), and DoD
  restrictions on DeepSeek reinforce that.

## Known weakness

Inkling sometimes reasons until it hits the output cap (2 of 15 fresh attempts,
both `entity-name-presence`), as its model card warns. The cap turns this into a
recorded `truncated_at_token_limit` failure rather than a hang. Lowering
`reasoning_effort` was not tried, because tuning on spent cases would not be
measurable. It needs a new decision.

## Not yet measured

- Held-out cases H1–H8. That is the result the sponsor's ">60% first pass" target refers to.
- The 0042 repair loop with Inkling. It has only been run with Gemma.

## Rules carried over from 0041

`--locked` selects this configuration and refuses overrides. Changing the
model, weights file, prompt, sampling or envelope parsing needs a new decision.
Earlier evidence keeps its recorded configuration and scores. Human approval
remains required for every patch.
