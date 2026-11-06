# Locked Gemma baseline and bounded repair — 5 November 2026

Configuration: decision 0041 (Gemma 4 31B via NVIDIA, semantic blocks 3.1),
repair protocol decision 0042 (at most two rounds, prompt `3.1-feedback`).
Public synthetic development benchmark. No patch was merged. Every passing
patch still requires human approval.

## Results

| Measure | Result |
| --- | --- |
| First pass (fresh locked baseline) | **6/8** |
| Validated within 1 repair round | **7/8** |
| Validated within 2 repair rounds | **7/8** |
| Held-out cases | 0/0 (none exist yet) |
| Model requests | 24 baseline + 9 repair |

The fresh baseline reproduced the earlier 6/8 with the same two failures.
This is a second sample of the same configuration, not new-case evidence.

| Case | First-pass stage | Round 1 | Round 2 |
| --- | --- | --- | --- |
| pubsub-utf8 | compilation | **validated** | — |
| inventory-width | response_or_edit_contract | response_or_edit_contract | response_or_edit_contract |
| six other cases | validated | — | — |

## pubsub-utf8: repaired by compiler feedback

The first pass passed a Protobuf `ByteString` where C# needed `byte[]`. The only
feedback was the compiler line
`runtimes/csharp/main.cs(21,78): error CS1503: cannot convert from 'Google.Protobuf.ByteString' to 'byte[]'`.
Round 1 decoded the bytes explicitly:

```diff
- fields = new() { ["entity_id"] = decoded.EntityId };
+ fields = new() { ["entity_id"] = System.Text.Encoding.UTF8.GetString(decoded.EntityId.ToByteArray()) };
```

It then passed compilation, unit tests, the independent pub/sub oracle and the
truncated-payload negative control.

## inventory-width: a response-format failure, not repaired

All three TypeScript responses (first pass and both rounds) had the same shape:
a complete JSON answer in a code fence, followed by prose such as *"Wait, I
noticed a mistake in my `edits` array…"* and a second, revised answer. The
parser accepts one JSON object or one fenced object and never extracts JSON
from prose, so each response was rejected as `Extra data`. The feedback carried
that error, but the model repeated the self-correction pattern.

This is an output-format compliance failure. Whether either embedded answer
would have migrated correctly was not evaluated. Changing the parser or the
feedback wording now would tune the protocol on an observed failure, so it
requires a new decision and must not be scored against these numbers.

## Limits

- All eight cases informed prompt development. Repair rounds also learn from the
  same finite checkers. These are development results, not held-out reliability.
- One sample per case and round; no significance claim.
- The summaries record `implementation_dirty: true` because the new evidence
  directory is untracked while running. Implementation code was committed at
  `8011557` before both runs.

## Evidence

- Baseline: `../nvidia-gemma-locked-001/summary.json`
- Repair: `summary.json` in this directory, with per-round `feedback.json`,
  raw requests and responses, validation logs and review bundles.
