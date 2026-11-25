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
- 2026-11-17 ~02:00: Codex (gpt-6.1-sol, memories disabled) authored 5 fresh
  cases. An independent read-only Cursor review (claude-opus-5-5-high) found
  the telemetry cases mostly tested C# float formatting, infrastructure errors
  scored as model failures, no attempt limit, and manifest gaps. Codex fixed
  all of them before sealing. One wrong patch was relabelled (rejected by an
  existing e2e test, not the fresh oracle).
- Dev screen (biased; prompt 3.1 was tuned on these cases): Gemma rerun 4
  validated, 1 model failure (pubsub-utf8 C# compile), then an NVIDIA 504 on
  telemetry-units stopped the cohort (3 cases not attempted). Mistral Large 4:
  5/8. A Muse Glimmer dev run was aborted by me within seconds so the ports
  were free for tests; it made no scored attempt and its directory was deleted.
- Before sealing: full patchgen suite 331/331 OK with loopback (no skips),
  `make test-unit` 29/29 OK, locked prompt fingerprints unchanged.

## Pre-registered fresh-screen protocol (written before any model run)

- Cases: exactly `FRESH_CASES` (5), sealed by `fresh-screen/manifest.json`,
  committed and pushed before the first model request.
- Models (in this order): Gemma 4 31B (locked config), Mistral Large 4,
  Muse Glimmer 30B, gpt-oss-20b (NVIDIA), North Mini Code (OpenRouter).
- Strategy `candidate_semantic_blocks` (prompt 3.1) for every model, no repair.
- Samples: 3 per model (`--sample 1..3`), run interleaved by sample (all
  models sample 1, then sample 2, then 3) so provider conditions are spread.
- Headline per model: validated / 15 attempts. Also reported: sample-1 only,
  per-case pass counts, failure stage, Wilson 95% interval.
- Infrastructure failures (HTTP 5xx/429, timeouts, connection errors) and
  cases a provider stop left unattempted are counted separately. One rerun of
  that sample is allowed with `--rerun-reason` (the runner always runs all five);
  only the cases that were infrastructure-failed or unattempted are taken from
  it, it is reported as a rerun, and it never replaces a model failure. Token-limit truncation counts as a model
  outcome (reported separately).
- No prompt, oracle, case or parser change after sealing. If a case proves
  broken, it is withdrawn for all models with the reason, not fixed.

## Extra run (deviation, NOT part of the pre-registered screen)

Written 2026-11-17, before any extra-run model request. Branch
`claude/amd-screen`.

Why: during the pre-registered screen NVIDIA's free endpoint returned many
504s, timeouts and connection errors (Mistral and Muse lost most cases), and
North Mini Code never ran because `pipeline.py` rejected its model id (exit 2,
zero requests; the runner wrongly labelled these "model" failures). The
pre-registered reruns were stopped early by the user's decision because NVIDIA
was too slow; finished reruns are kept, the in-progress Mistral sample-2 rerun
is recorded as aborted.

What changed (code only, no case, fixture, oracle or prompt change; the
manifest diff shows `cases`, `split` and `prompt_fingerprints` identical):
- New `--backend amd` (`patchgen/amd_client.py`, `https://api.tokenlab.amd.com/v1`),
  model `Gemma-4-31B-IT` with the exact locked Gemma options (temperature 0.5,
  top_p 1, seed 0, max_tokens 4096). Purpose: same model, different provider.
- `pipeline.py` accepts all OpenRouter screening models (North Mini Code fix).
- Zero-request failures are labelled `harness` and counted separately.
- Original seal kept as `fresh-screen/manifest-v1-preregistered.json`
  (sha256 6b9b9c71…). Extra-run seal: `fresh-screen/manifest.json`
  (sha256 511b83e3…).

Extra-run protocol: 3 samples each, interleaved by sample: AMD Gemma, then
North Mini Code (OpenRouter), `candidate_semantic_blocks`, no repair, one run
at a time. Same counting rules as above. These numbers are reported in their
own table and never added to the pre-registered headline. Other AMD models were
not used: DeepSeek, Qwen and MiniCPM are Chinese-origin (user preference);
Clef, d3 and d3-flash are not chat models.

## Result

See `docs/decisions/0043-post-lock-model-screening.md`. Summary: keep 0041;
Gemma 9/15 on NVIDIA and an identical per-case pattern on AMD; gpt-oss-20b
4/15; North Mini Code 0/15 (extra run); Mistral Large 4 and Muse Glimmer not
measurable because of NVIDIA provider failures.

## Repair-loop trial on the fresh failures (written before any repair request)

Source: the three pre-registered locked Gemma runs (`fresh-gemma-s1..s3`), each
with 2 rejected cases (`telemetry-speed-presence`, `inventory-state-bool`), so
6 repair targets. `repair_suite --max-rounds 2` (decision 0042), NVIDIA, locked
Gemma, prompt `3.1-feedback`, run one source at a time.

Fix made first: `repair_suite.ORACLES` did not include the fresh oracle, so its
verdict never reached the model (only "another check rejected the proposal").
The verdict now arrives in the existing fixed wording (runtime name only; no
values or vector contents; covered by a test).

Reported: validated within 1 round and within 2 rounds, out of 6 targets, and
per case. A repaired pass is never counted as a first-pass success. The
feedback comes from the same oracle that scores the result, so this measures
"can it fix the patch when told which runtime failed", not first-pass
quality. Gemma at seed 0 gave identical first passes, so the 3 sources are
close to one target per case; that is stated with the result.

## Second extra run: Inkling 2 Mini vs Gemma under rule 0044 (deviation, NOT pre-registered)

Written 2026-11-25, before any request in this run. Branch `claude/selfhosted-inkling`.

Why: to compare Inkling 2 Mini (Thinking Machines, US, Apache 2.0, 26B total / 3.4B active, fits the
sponsor's one-GPU workstation path) with locked Gemma on cases neither was tuned on. The extra-run seal no
longer matches the code, so this run needs its own seal.

What changed since the extra-run seal (code only; no case, fixture, oracle or prompt change):
- Decision 0044 (`anchor_edits.py`): whole-line edits missing only the final newline are now accepted.
  **This changes scoring**, so earlier fresh numbers (Gemma 9/15) are not comparable. Gemma is therefore
  re-run here under the same code.
- New `--backend selfhosted` (`patchgen/selfhosted_client.py`): llama.cpp on one AMD MI300X (AMD Developer
  Cloud), reached only through an SSH tunnel. GGUF `ggml-org/Inkling-2-Mini-GGUF` `Inkling-2-Mini-Q8_0.gguf`,
  sha256 `652b8594fa321dadbd6af4966aa1c22578c7746ba2faa4c0046b3c108075274a`, llama.cpp build b12723-abca69200,
  served as `inkling-2-mini-q8_0`. Sampling: temperature 1.0 (the model's generation config), seed 0,
  max_tokens 16384, reasoning_effort "high" (the chat template's default).
- Devstral 2 added to the OpenRouter allow-list (never ran).
- Seal diff (checked before any request): `cases` and `split` identical; `prompt_fingerprints.one_shot` and
  `.repair` identical (prompt text unchanged); only `prompt_fingerprints.protocol` changed, because it hashes
  `anchor_edits.resolve`, which 0044 changed. Changed files: anchor_edits.py, generator.py, live_suite.py,
  openrouter_client.py, pipeline.py.
- Extra-run seal kept as `fresh-screen/manifest-v2-extra.json`; this run's seal is `fresh-screen/manifest.json`
  (sha256 cb1b16ad…).

Protocol: 3 samples each, `candidate_semantic_blocks`, no repair. Gemma via `--backend amd` (TokenLab,
locked options). Samples run concurrently (the server has 4 slots). Same counting rules as above.
Inkling had already seen the 8 development cases (8/8) earlier the same day; it had never seen a fresh case.
Reported in its own table, never added to the pre-registered headline. The fresh cases have been seen by
the people tuning this pipeline since 2026-11-17, so this is a screening comparison, not a held-out result.

First attempt (2026-11-25, attempts 1-6 in `fresh-screen/attempts.jsonl`): every sample stopped on its first
case with infrastructure failures, before any model failure. Inkling: HTTP 500 "Context size has been
exceeded"; my server setup was at fault (llama.cpp `-c 32768` is one KV cache shared by all slots, and three
concurrent samples at ~11k tokens each overflowed it). Gemma: TokenLab HTTP 503 (Retry-After 10) with three
concurrent samples. Fix before rerun: server restarted with `-c 131072` (same GGUF, build, alias and
sampling); Gemma samples run one at a time. Reruns are recorded with `--rerun-reason`; no model failure is
replaced. One Gemma case passed in the first attempt (s3 entity-name-presence); it is reported but the
rerun's results are the ones counted.
