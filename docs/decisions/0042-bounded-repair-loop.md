# Decision 0042: bounded repair loop and evaluation-bias guards

Implements the proposal's repair-loop item on the locked configuration (0041).
`patchgen/repair_suite.py` takes a completed `live_suite --locked` run and, for
each rejected case, sends validation diagnostics back to the model for at most
two rounds. Each round makes one request per original runtime file. Strategy
`candidate_semantic_feedback_blocks` (prompt `3.1-feedback`) extends the locked
3.1 prompt with feedback rules. It is allowed on the NVIDIA backend only.

```sh
.venv/bin/python -m patchgen.live_suite --locked --full-benchmark --output patchgen/evidence/NEW-locked
.venv/bin/python -m patchgen.repair_suite --source patchgen/evidence/NEW-locked --output patchgen/evidence/NEW-repair
```

## What feedback may contain

- Compiler errors whose own location is a file the model edited, with local paths
  removed. Errors located in evaluator-owned test files are withheld and only
  counted, even when their message mentions an edited file.
- Python syntax errors from the generator report, mapped to the owning file.
- The file's own edit-contract or JSON-envelope rejection.
- A fixed-wording oracle verdict, such as `telemetry runtime check failed at
  authored case 1 in the csharp service`. Oracle error text is never copied,
  because it can contain expected values (the pub/sub oracle names expected
  message IDs). Vectors, reference patches and raw build logs are never sent.

## Bias guards

| Concern | Guard |
| --- | --- |
| Silent tuning after the lock | `LOCKED_PROMPT_SHA256` fingerprints the one-shot and repair prompts (including the binding-specific branch), plus the prompt allowlist, edit resolver, JSON-envelope parser and sampling options. Locked and repair runs refuse to start if any changed, and a unit test fails. The repair runner also checks every retained request actually sent the locked model and sampling. |
| Repaired passes reported as first-pass | First-pass, within-round-1 and within-round-2 counts are separate fields. Round 0 comes only from the full acceptance flag; a run whose checks passed without exit code 0, live mode and a review bundle is `incomplete_acceptance`. The source suite must have `automatic_repairs: 0`. |
| Format failures mixed with behavior failures | Every case reports a stage: `response_or_edit_contract`, `compilation`, `runtime_semantics`, `incomplete_acceptance`, `validated`, or provider/infrastructure. |
| Scoring on cases used for prompt development | Every result carries a `development` or `held_out` split. All eight current cases are `development`, so the summary shows `held_out: 0/0`. |
| Answer leakage through feedback | The rules above, with tests that plant expected values, oracle vectors and hidden test errors and assert none reach the prompt. |

## Not addressed by this change

- **No held-out cases yet.** Only new migrations, authored after the lock and
  never used to adjust prompts, can show unseen-case reliability.
- **Supplied semantics.** `intended_behavior` states conversions such as the
  3.6 factor. We measure whether the model implements given semantics, not
  whether it discovers them.
- **Shared authorship.** We wrote both the requirements and the checkers. A
  teammate or sponsor should review held-out requirements and expected behavior.
- **Finite vectors.** Runtime oracles check fixed authored cases; property-based
  inputs would broaden them.
- **One sample per case.** No significance claim is made from 8 cases.
- **Repair adapts to the same checkers.** Retries still learn from the same finite
  oracles. Report repaired results as development evidence only.

An independent read-only Codex review of this change found the oracle-text
leak, the first-pass classification gap, the narrow fingerprint and the loose
compiler filter. All four are fixed above and covered by tests.

Unit tests (282 in total) are implementation checks, not migration cases.
Human approval remains required for every patch, repaired or not.
