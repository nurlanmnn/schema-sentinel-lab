# Live model evaluation — November 2, 2026

## Frozen 8B baseline

The six-case live run produced **0/6 validated proposals** from **18 actual model
requests**. This is an unsuccessful model baseline, separate from the seven
successful deterministic migrations and known-answer evaluator replays.

Model: local `ministral-3:8b`, digest
`1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71`.
Prompt 2.5 (`candidate_edits`), temperature 0, seed 42, context 16384,
output limit 8192. One request per runtime file; no repair loop or fallback.
The exact requests, model responses, serving counters, source snapshots and
rejected review bundles remain in
`patchgen/evidence/live-six-ministral8b-001/`.

| Case | First blocking gate | Observed detail |
| --- | --- | --- |
| Pub/sub rename | Compilation | TypeScript dropped a declaration. Inspection also shows old accessor reads retained in all three languages. |
| Pub/sub removal | File contract | Python reviewed lines outside the supplied candidate set. |
| Pub/sub UTF-8 | File contract | C# edits contradicted candidate decisions; inspection also shows a v2-only migration modifying v1 code. |
| Telemetry rename | File contract | C# and Python omitted candidate reviews. Inspection shows old accessor reads retained. |
| Telemetry precision | File contract | TypeScript supplied overlapping edit ranges. |
| Telemetry units | Independent semantics | Builds and existing Entity relay checks passed; C# JSON did not expose the exact decoded float32 observation. |

Thirteen of eighteen file responses passed the edit contract. That is a format
result, not thirteen correct files or validated patches. Four cases were blocked
before compilation; their runtime behavior is unestablished. The table records
the first blocking gate and distinguishes additional source inspection.

The units example demonstrates why compilation is insufficient. For the adopted
29.5 m/s input, the oracle expects `speed_kph=106.19999694824219`, the exact decoded
float32 value represented as a JSON number. C# emitted `106.2`. Producer wire bytes
and the threshold decision matched for that sample, but observation equality did
not. The intended behavior explicitly requires exact decoded float32 observations;
the gate was not relaxed to accept the generated proposal.

Full per-request timing and concrete contract/compiler diagnostics are in
`patchgen/evidence/live-six-ministral8b-analysis001/analysis.md`. Generation took
about 14.1 minutes and the prepared pipelines about 14.5 minutes in total. The
first request's Ollama load counter was about 14.27 seconds; subsequent load
counters were about 0.13–0.19 seconds. These are recorded serving counters, not a
controlled cold/warm benchmark or operational propagation measurement.

## Next experiments

Prompt 2.8 (`candidate_blocks`) is a separate in-sample development experiment
using the same 8B digest and six inputs. It requires fixed candidate IDs through
the response schema and asks the model for exact source blocks. The host authors
no runtime replacements. Its results must be reported separately, with the same
compilation and independent semantic gates; see decision 0022. Its completed run
also produced **0/6 validated proposals from 18 live requests**. File contract
passes increased from 13/18 to 16/18, with about 12.7 minutes of generation. This
format improvement did not produce a successful migration. The paired audit in
`patchgen/evidence/live-8b-prompt-comparison001/` found the same generation inputs,
inference options and captured validation gates and classifies this as prompt
development, not a model comparison.

| Prompt 2.8 case | First blocking gate |
| --- | --- |
| Pub/sub rename | TypeScript compilation: old property names retained |
| Pub/sub removal | Python syntax: empty `if` blocks after deleting statements |
| Pub/sub UTF-8 | Contract: unchanged replacement block |
| Telemetry rename | C# compilation: old accessor retained in the threshold check |
| Telemetry precision | Contract: unchanged replacement block; source inspection also shows an unrelated C# semicolon deletion |
| Telemetry units | Independent semantic observation mismatch |

Raw evidence is in `patchgen/evidence/live-six-ministral8b-blocks001/` and analysis
in `patchgen/evidence/live-six-ministral8b-blocks-analysis001/`. A separate bounded
feedback probe on the selected failed rename case is described in decision 0023;
it has a different protocol and is not included in either one-shot rate.

Model choice remains unresolved. [Mistral's official documentation](https://docs.mistral.ai/models/ministral-3-14b-25-12)
identifies Ministral 3 14B under Apache-2.0. The
[official Ollama package](https://ollama.com/library/ministral-3:14b) is a roughly
9.1 GB Q4_K_M download. It is a plausible larger comparison, not a demonstrated
solution or a guaranteed fit on this 16 GiB Mac. Download authorization is
pending; no 14B result exists. A fair model comparison must keep prompt 2.5,
the six inputs, options and validation gates fixed before testing prompt changes.

These six authored cases are development evidence, not the twenty-case MVP,
held-out general reliability, human manual baseline, human approval or deployment.
