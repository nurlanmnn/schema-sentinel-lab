# Decision 0043: post-lock model screening — keep the 0041 lock

Status: recommendation. The 0041 lock (Gemma 4 31B, prompt 3.1) is **not**
changed; changing it needs the user's decision. Plan, pre-registered protocol
and the extra-run deviation: `docs/patch-generation/model-screening-plan.md`.
Per-case data for every run: `fresh-screen/results-summary.json`; attempt
ledgers: `fresh-screen/attempts-v1-preregistered.jsonl`, `attempts-extra.jsonl`.

## Outcome

No candidate gave evidence of doing better than Gemma. Gemma's result
reproduced on a second provider. Mistral Large 4 could not be measured because
NVIDIA's free endpoint failed most of its requests.

### Pre-registered fresh screen (seal 6b9b9c71…, 5 cases × 3 samples)

| Model | Validated | Model failures | Infra / not attempted | Validated of scored | Wilson 95% (of 15) |
| --- | --- | --- | --- | --- | --- |
| Gemma 4 31B (NVIDIA, locked) | **9** | 6 | 0 | 9/15 | 36–80% |
| gpt-oss-20b (NVIDIA) | 4 | 10 | 1 | 4/14 | 11–52% |
| Mistral Large 4 (NVIDIA) | 4 | 0 | 11 | 4/4 | not meaningful |
| Muse Glimmer 30B (NVIDIA) | 1 | 0 | 14 | 1/1 | not meaningful |
| North Mini Code (OpenRouter) | — | — | 15 (harness bug) | not evaluated | — |

- Gemma passed `entity-name-presence`, `telemetry-asset-rename` and
  `inventory-quantity-unsigned`, and failed `telemetry-speed-presence` and
  `inventory-state-bool`, identically in all three samples (seed 0). Its 15
  attempts therefore behave like about 5 independent ones.
- Mistral and Muse counts include the pre-registered reruns that finished
  (Mistral s1; Muse s1, whose only pass came from the rerun). The reruns were
  stopped early by the user's decision because NVIDIA was too slow. An
  in-progress Mistral s2 rerun was aborted, and the Mistral s3, Muse s2/s3 and
  gpt-oss s3 reruns never ran. Mistral's 4/4 is too small to compare.
- North Mini Code sent zero requests: `pipeline.py` rejected its model id. The
  sealed runner mislabelled these runs as model failures; they are counted here
  as not attempted.

### Extra run (deviation, seal 511b83e3…, same 5 cases, code-only change)

| Model | Validated | Model failures | Infra / not attempted | Validated of scored | Wilson 95% (of 15) |
| --- | --- | --- | --- | --- | --- |
| Gemma 4 31B (AMD TokenLab, locked options) | 7 | 3 | 5 | 7/10 | — |
| North Mini Code (OpenRouter, fixed) | 0 | 15 (2 at the 16384-token limit) | 0 | 0/15 | 0–20% |

- AMD Gemma matched NVIDIA Gemma on every case both providers scored: it passed
  entity, asset-rename and quantity-unsigned, and failed speed-presence in all
  three samples. So the locked result is a property of the model and prompt,
  not of NVIDIA.
- Every AMD failure was an HTTP 503 ("temporarily unavailable") at exactly
  60 s, including the first request of `inventory-state-bool` in all three
  samples. This looks like a 60-second gateway cap on long generations. It is
  inferred from the timing and not confirmed by AMD.

## Limits (read with every number)

- The cases were written by Codex, not an independent human evaluator. Two of
  the five reuse known mechanisms and two carry anchor hints. This is **not**
  the held-out set; H1–H8 remain unspent.
- Prompt 3.1 was tuned on Gemma's failures. This measures "drop-in under 3.1",
  not each model's best.
- Reasoning models got 32768 output tokens (North: 16384), versus Gemma's 4096.
- The sample counts are small, so no significance claims are made. Only Gemma
  (both providers), gpt-oss-20b and North Mini Code have enough scored attempts
  to read at all.
- The extra run is outside the pre-registration. Its numbers are never added to
  the headline.

## Recommendation

1. Keep 0041. Drop gpt-oss-20b and North Mini Code as candidates.
2. Mistral Large 4 is the only open question. Measure it only on a provider that
   can answer reliably, under the same sealed cases, as another labelled run.
3. The larger lever is Gemma's two failures that never change
   (`telemetry-speed-presence`, `inventory-state-bool`). The bounded repair loop
   (0042) has never been run live; running it on these failures is the
   cheapest next experiment. Any prompt change must be judged on cases it was
   not tuned on.

## Addendum: repair loop and the trailing-newline rule (2026-11-17)

**Repair loop (0042), first live run** on Gemma's 6 rejected fresh attempts
(two cases × three samples), 2 rounds max, NVIDIA:

| Case | Round 1 | Within 2 rounds |
| --- | --- | --- |
| `telemetry-speed-presence` (wrong behavior in TypeScript) | 0/3 | 1/3 |
| `inventory-state-bool` (edit-format rejection) | 0/3 | 0/3 |

Before the run, a bug was fixed: the fresh oracle was missing from
`repair_suite.ORACLES`, so its verdict never reached the model. Repaired passes
are not first-pass successes, and the feedback comes from the same oracle that
scores the result.

**Why `inventory-state-bool` never passes:** `anchor_edits.resolve` rejects an
edit whose `before` text is a run of complete source lines without the trailing
`\n`. The error text ("before must contain complete source lines") does not say
that, and Gemma repeated the omission in every repair round. Across all
retained evidence, 23 of the 26 rejections with this message would apply after
appending the newline (Gemma 10, North Mini Code 9, gpt-oss 3, Laguna 1).

**Offline counterfactual** (`patchgen/newline_replay.py`; recorded responses
only, no model requests; results in `patchgen/evidence/newline-replay/`):
appending only the missing trailing newlines, with every other byte unchanged
(verified), lets **all three** recorded first-pass `inventory-state-bool`
answers pass full validation (30 oracle cases each). A control case that had
already validated still validates. The six repair-round answers clear the edit
contract, but the CLI refuses offline replay of the feedback strategy, so their
full-validation outcome is unknown.

Read carefully: with this rule relaxed, Gemma's fresh first-pass score would
have been 12/15 rather than 9/15. That is a post-hoc counterfactual on cases
already seen. It is not a measured score. The other models were not replayed.

**Recommendation (needs the user's decision; changes how the locked
configuration is scored):** either have the harness append a missing trailing
newline when `before` otherwise matches whole lines exactly once, or change the
error text to name the missing newline. Then measure the effect only on cases
not used to find it (the unspent held-out set). Until then, 0041's numbers stand
as measured.
