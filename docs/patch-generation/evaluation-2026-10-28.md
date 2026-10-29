# Runtime patch-generation evaluation — 28 October 2026

**One live runtime-only proposal passed local validation.** The model generated
Python, TypeScript and C# runtime edits to remove `Entity.name` while retaining
`entity_id`. The host copied the supplied new schema, regenerated Protobuf
bindings with the existing pinned Buf plugins, and evaluated the proposal using
a separately maintained test migration. This was not a successful generation
of test changes and was not the first attempted configuration.

## What changed

The failed direct-diff experiment is untouched. File-scoped JSON-schema requests
were added, followed by exact-anchor, complete-file and numbered-line strategies.
The current prompt 2.3 returns line ranges and replacement-line arrays; the host
owns paths and diff assembly. It checks original revision/context, edit ranges,
no-ops, overlap, supplied impact coverage, Python syntax and original test names.
A malformed or incomplete proposal is retained and rejected without repair.
There is one request per supplied file and no automatic feedback/repair loop.

The working fixture lists only runtime files. Its opt-in validation profile is
pinned to source/schema/test-patch hashes and permits changes only to two test
files. Reference runtime answers and evaluator-owned test source are excluded
from these model requests. The old five-file fixture remains available; every
live attempt to generate both runtime and test migrations failed.

## Recorded attempts

| Attempt | Local model | Prompt | Prepared workflow elapsed | Result |
| --- | --- | --- | --- | --- |
| live-001 | ministral-3:3b | 1.0 | 33.6 s | Malformed multi-file diff; runtime changes omitted |
| live-002 | ministral-3:3b | 2.0 | 49.6 s | 3B exact anchor mismatch |
| live-003 | ministral-3:8b | 2.0 | 152.5 s | 8B test anchor mismatch |
| live-004 | ministral-3:8b | 2.1 | 363.5 s | C# compile failure; invalid removed property retained |
| live-005 | ministral-3:8b | 2.2 | 160.6 s | Missing line terminators and a no-op |
| live-006 | ministral-3:8b | 2.3 | 168.2 s | Test no-ops and edits outside supplied sites |
| live-007 | ministral-3:8b | 2.3 | 61.0 s | PASS: runtime generation with independent test migration |

These attempts changed configuration and generation scope; they are not a
controlled model comparison, patch-success-rate benchmark or first-pass metric.
The 23 October attempt is included as history. Each failed run retains raw
responses and errors. No response was edited into a passing answer.

## Passing evidence: live-007

- Exact source revision: `26304c1ed2f4738676a9607e8fe21e17ebd090f0`.
- Model: Mistral AI Ministral 3 8B Instruct 2512, local tag `ministral-3:8b`.
- Digest: `1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71`.
- GGUF Q4_K_M; Ollama metadata reports 8.9B parameters. Ollama 0.30.8.
- Hardware: Apple M4 MacBook Pro, 16 GiB unified memory.
- Request settings: temperature 0, seed 42, context 16,384, output limit 8,192.
- Three warm local model requests: 16.699 s, 16.504 s and 17.096 s (50.299 s total).
- Maximum sampled Ollama model allocation: 7,352,174,508 bytes (about 6.85 GiB),
  not whole-system peak RSS. Exact samples and server token timings are retained.
- This prepared-fixture workflow: 61.023 s. The separately timed one-model
  download took 98.603 s. These are not general schema propagation performance,
  human review time, a human manual baseline or mixed-version latency.

The 8B model is Apache 2.0 and developed by Mistral AI; Ollama is MIT. This
continues the open-source/non-Chinese model constraint using existing local
hardware. No paid compute, fine-tuning or second new model download was used.
Primary sources: [model release](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512),
[Ollama artifact](https://ollama.com/library/ministral-3:8b),
[structured output API](https://docs.ollama.com/capabilities/structured-outputs).

Validation log records configured regeneration, TypeScript and .NET builds,
11 existing unit tests and four round trips. The independent oracle checks
field declarations, four fixture categories, six invalid-evidence rejections,
and five payload cases including a legacy field-2 payload. All decoder maps
contained only `entity_id`, final values survived, and service order was correct.
Six additional standalone checks (v1/v2 in each runtime) preserved the expected
identifiers and only reported `entity_id`. These are local macOS observations;
there is no new cross-platform CI evidence.

The generator test suite passes 29 tests, including profile pinning, preventing
model edits to trusted tests, missing inputs, stale revision, unsafe paths,
malformed diffs, ambiguous/overlapping edits, line coverage, reference exclusion,
source snapshot provenance, weakened evidence and non-patch outcomes.

## Review and replay

Run the one-command example in README.md. Its output directory must be new.
`live-007/proposal.patch` is the model runtime proposal plus supplied schema.
`live-007/validation-tests.patch` identifies the independent test migration.
`live-007/validated.patch` is the complete review bundle, including generated
bindings. `report.json` explicitly records this generation boundary and still
requires human approval. Implementation snapshots, model metadata, prompts,
requests, raw responses, measurements and validation logs are retained.

The raw Python proposal leaves a redundant adjacent `fields = {"entity_id":
entity.entity_id}` assignment. It does not change the result, but remains visible
for human cleanup; the saved proposal was not manually corrected.

Limitations: one manually located field-removal case; trusted test migration
is case-specific; no successful model-generated test migration; no automatic
detector/locator integration; no 20-case evaluation; confidence remains subjective
and uncalibrated; human acceptance is pending. No push, merge or deployment.
