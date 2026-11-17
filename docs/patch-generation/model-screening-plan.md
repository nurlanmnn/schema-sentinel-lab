# Post-lock model screening plan (draft decision 0043)

Status: in progress, started 17 November 2026. Branch
`claude/model-screening-fresh-cases`. Decision 0041 (locked Gemma/3.1) is
**not** changed by this work; any change to the lock needs the user's OK and a
new decision.

## Why

The user asked whether a newer model does better, and asked for results that
are not misleading. The existing 8 live cases shaped prompt 3.1, which was
itself tuned partly on Gemma's failures, so a score on them is biased in
Gemma's favour. Two separate measurements are therefore taken and never summed:

1. **Development screen (biased, cheap).** Each candidate runs the unchanged
   prompt 3.1 on the 8 development cases. Useful only to drop models that fail
   badly (format errors, provider problems).
2. **Fresh screen (less biased).** New cases written by Codex with memories
   disabled and told not to read model outputs, sealed by SHA-256 manifest and
   pushed to GitHub *before* any model sees them. Every model, Gemma included,
   runs each case once with the same prompt. This is not the official held-out
   set (that still needs an independent human evaluator, see
   `held-out-plan.md`); H1–H8 are deliberately not used so they stay unspent.

## Remaining known biases (report these with every number)

- The case author (Codex) can read the repo and the prompt; it was told not to
  read evidence or failure write-ups, but it is not a human independent evaluator.
- Prompt 3.1 was tuned on Gemma; other models may need their own prompt. We do
  not tune per-model prompts here, so this screen measures "drop-in under 3.1".
- One sample per case per model; small n. Report counts plus Wilson 95%
  intervals and no significance claims.
- `intended_behavior` spells out semantics; we measure implementation, not
  discovery of semantics.

## Candidates (non-Chinese, reachable with existing keys)

| Model | Route | Why |
| --- | --- | --- |
| `google/gemma-4-31b-it` | NVIDIA | locked baseline |
| `mistralai/mistral-large-4-1t-a52b` | NVIDIA | frontier open-weight MoE, strong reported coding scores |
| `meta/muse-glimmer-30b` | NVIDIA | Meta claims it beats Gemma 4 31B on coding |
| `openai/gpt-oss-20b` | NVIDIA | small US open-weight model |
| `cohere/north-mini-code:free` | OpenRouter | coding-specialised 30B-A3B, Apache-2.0 |

Excluded: Chinese-origin models (user preference), models already tried
(Nemotron Ultra/Super, Laguna, DeepSeek, Ministral).

## Steps

1. Allow candidates in the transports with provider-recommended sampling; keep
   the locked fingerprint unchanged (unit tests prove it).
2. Development screen of each candidate on the 8 dev cases.
3. Codex authors 5 fresh cases (fixture, oracle with boundary vectors,
   reference patch that passes, at least 3 wrong patches that fail).
4. Review validity only (not difficulty), seal manifest, commit, push.
5. Fresh screen: every model once, all attempts retained.
6. Write results to `patchgen/evidence/screen-*/summary.md` and record decision
   0043 with the outcome and limits.

## Log

- 2026-11-17: NVIDIA probes: Mistral Large 4 and Gemma answer; Muse Glimmer
  and Nemotron Lightning returned empty content at 64 tokens (likely reasoning
  output); gpt-oss-20b timed out at 120 s.
