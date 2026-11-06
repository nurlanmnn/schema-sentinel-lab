# Bounded repair loop plan

Status: plan only. Nothing here is implemented yet.

The proposal's home-run item asks for a repair loop: when a generated patch
fails validation, send the compiler and test output back to the model and let it
retry a fixed number of times, then report how much that raises the first-pass
rate. This plan applies it to the locked configuration (decision 0041).

## What already exists

- `patchgen/feedback_blocks.py`: prompt `2.9-feedback`. It carries the previous
  response plus host diagnostics. It builds on the older non-semantic block prompt.
- `patchgen/feedback_probe.py`: up to two rounds on one failed case. Local Ollama
  only (it checks the Ministral digest). Decision 0023.
- `patchgen/live_analysis.failure_evidence`: extracts compiler and oracle diagnostics.
- `patchgen/generator.py` rejects `candidate_feedback_blocks` on hosted backends.

## Protocol

1. Run a fresh locked one-shot suite on the eight live-eligible cases. This is the
   first-pass number. It is also a second sample of the 6/8 result.
2. For each rejected case (not `provider_unavailable`), run at most two repair
   rounds, with one request per original runtime file per round. Stop a case as
   soon as every original validation gate passes.
3. Use the same model, sampling, source revision, schema, edit contracts,
   compilation/unit checks and independent runtime oracles. Feedback contains only
   the previous response and host diagnostics. It never contains reference patches,
   expected values or oracle source.
4. Report first pass, after round 1 and after round 2 as separate numbers, plus
   per-case outcomes and cumulative request counts. A repaired pass is never
   counted as a first-pass success.

Upper bound: if two cases fail, 2 cases × 2 rounds × 3 files = 12 extra requests,
on top of the 24 baseline requests.

## Code changes

1. `feedback_blocks.make_prompt`: add a semantic variant built on
   `candidate_semantic_blocks`, version `3.1-feedback`. Keep `2.9-feedback`
   unchanged for reproducing decision 0023.
2. `generator.py`: allow the semantic feedback strategy on the NVIDIA backend for
   the locked model only.
3. New `patchgen/repair_suite.py` (generalizing `feedback_probe.py`): take a
   completed suite whose summary has `locked_configuration: "0041"`, iterate over
   its rejected cases, and replace the Ollama digest check with the existing
   provider identity check.
4. Diagnostics: keep the current extraction, cap each file's diagnostics, and
   include envelope rejections such as "extra text after JSON".
5. Tests, all on synthetic loopback responses: refuse validated or unlocked
   sources, enforce the round bound, never merge repaired passes into the
   first-pass count, and stop on provider errors.

## Known targets

From the Gemma/3.1 run: `pubsub-utf8` failed C# compilation (a `ByteString`
was passed where `byte[]` is required). `inventory-width` was rejected because
TypeScript output had extra text after the JSON. Both are failures the feedback
should be able to correct. A fresh baseline may fail on different cases.

## Limits

These eight cases informed prompt development, so results remain development
evidence, not held-out reliability. The other twelve benchmark cases stay outside
the live route. Human approval is required for every patch, repaired or not.
