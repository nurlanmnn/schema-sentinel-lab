> **Start with the [main README](../../README.md#patch-generation-validation-and-review-steps-3-to-5)**
> for the current patch-generation overview: locked Gemma setup, repair loop, results and commands.
> This page is the original local-model write-up. Some statements are out of date: it says
> there is no repair loop, and it describes only local models.

Independent Lab continuation: [descriptor/locator pipeline](independent-pipeline.md)
and [earlier measurements](../history/independent-results.md). The historical results below
remain intact; the independent path adds measured runtime candidate production.

# Local patch-generation example

The working path generates runtime edits only and validates them against a
separate trusted test migration. Model-generated test migration is still an
unsuccessful experiment. This is a review-only SS-70/71/72 slice. It accepts manually prepared impact sites,
makes one request per supplied file, stores evidence and checks a proposal in a detached
worktree. No repair loop or automatic merge is implemented.

Install Python 3.13, Node 22+, .NET 8 SDK, Buf, and Ollama. Buf uses the existing
pinned plugins in `buf.gen.yaml`; their registry must be reachable. The runtime
setup uses existing dependency manifests and lockfiles. On macOS, install Buf
with `brew install bufbuild/buf/buf`. Start `ollama serve` if needed, then
`ollama pull ministral-3:8b`. Model setup is separate from request measurement.

One command prepares the exact source, produces and evaluates a new proposal
(run from this implementation checkout):

```sh
python3 -m patchgen.generator --prepare-source --model ministral-3:8b --fixture patchgen/fixtures/entity-name-removal/runtime-input.json --validation-profile entity-name-removal --output patchgen/evidence/my-run --validate
```

`--prepare-source` creates a detached snapshot at the fixture commit under the
new output directory. To use an existing checkout, omit that flag and pass
`--source PATH`; its HEAD and file text must match the fixture exactly.

The output directory must be new. The default fixture is the original broader
five-file experiment; use the runtime-only command above for the passing scope.
Use `--fixture` for another contract record. Both local `ministral-3:3b` and
`ministral-3:8b` are allowlisted; no cloud model or remote endpoint is accepted. `--validate` runs `buf generate`, the
existing `run_local.py` setup/build/unit/round-trip checks, then an independent
oracle with four field-value cases plus a legacy field-2 payload. Without that
flag the result is explicitly `applied_unvalidated`. Failures exit nonzero.
The model cannot select commands or modify generated files. Paths, modes,
revision and context are checked before application. `git apply --check` rejects
malformed or nonapplicable patches. Application never modifies the source tree.
A detached worktree is filesystem isolation, not a hostile-code security sandbox;
this example is for the supplied public, trusted testbed and local model.

Retained artifacts: input, prompt version/hash, exact request/settings, model tag
and digest/quantization/license metadata, serving version, raw response, proposal,
diff, request-time allocation samples, report, validation log and worktree. A
failed attempt is retained without repair or manual correction of its response.
After passing validation, `validated.patch` also includes regenerated bindings
and, when explicitly selected, the independent test migration. Review this
complete bundle; `proposal.patch` alone is the model runtime edits plus the
supplied schema and does not include the evaluator-owned tests. The selected
profile and its source/schema/test-patch hashes are saved separately.
Model usefulness is assessed separately from offline harness correctness.
Each new run saves `generator-source.py` and `oracle-source.py`; the report
contains their hashes. Command logs include individual elapsed durations.
Nested source/application worktrees and installed dependencies are ignored by Git.

Prompt 2.3 requests small line-range replacements using an Ollama JSON schema.
The source is numbered with original 1-based lines. Ranges must be valid and
nonoverlapping, and every supplied impact line must be covered. Each replacement
is an array of source lines; the host supplies line separators. The host owns the path,
copies the supplied new_schema, and assembles a unified diff.
`--strategy exact_edits` selects prompt 2.0; `--strategy file_content` selects
prompt 2.1. Both remain available for reproducing the earlier experiments. There is one request per file and no repair loop.
A clarification or invalid file blocks partial application. Raw responses are
retained under `requests/01/` through `05/` for the original five-file fixture (three requests for the runtime-only fixture). The independent
oracle also checks six deliberately bad evidence cases to detect weakened
assertions and verifies that the original four test categories still exist. Python syntax and retention of original unit-test names are checked
before running builds. Human review remains required even after validation.

Offline reference verification (does not call a model):

```sh
python3 -m patchgen.generator --prepare-source --response patchgen/reference/entity-name-removal/response.json --output patchgen/evidence/offline-reference-replay --validate
```

Tests: `python3 -m unittest discover -s patchgen/tests -v`.
No-change and clarification outcomes are valid reports, not validation successes.
Confidence is uncalibrated. Request time includes local inference/loading and
sampling overhead; server-reported load/evaluation durations remain in the raw
response. Model memory is sampled Ollama allocation, not system peak RSS. None of
these measurements are human review time, a human manual baseline, per-message
latency, or general schema propagation performance.

Review every generated patch and its evidence before acceptance. Automatic
change detection/location, pub/sub, mixed-version guarantees, a 20-case benchmark,
license adoption by the team and human acceptance remain separate work.


Current result: see `evaluation-2026-10-28.md`. One live runtime-only run passed;
there is no successful live generation of both runtime and test migrations.
The validation profile is opt-in, pinned to this exact change/revision, and only
allows two evaluator-owned test files. Test sources and reference answers are
not passed to the runtime model. To repeat the broader failed scope, use the
original `input.json` fixture without `--validation-profile`.


Three-case expansion: [benchmark seed report](../history/benchmark-seed-2026-10-28.md).
Live rename/type proposals failed; an unused enum addition passed with no runtime
edits. Independent rename/type reference replays passed separately. Run
`python3 -m patchgen.benchmark --output patchgen/evidence/benchmark-next` for all
three live cases sequentially. See [adapter 1.0](adapter.md) for fixture-fed wiring
and the real prototype's measured 2/6 impact recall; full integration is pending.
