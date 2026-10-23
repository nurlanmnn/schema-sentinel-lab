# Local patch-generation example

This is a review-only SS-70/71/72 slice. It accepts manually prepared impact sites,
calls a local model once, stores evidence and checks a proposal in a detached
worktree. No repair loop or automatic merge is implemented.

Install Python 3.13, Node 22+, .NET 8 SDK, Buf, and Ollama. Buf uses the existing
pinned plugins in `buf.gen.yaml`; their registry must be reachable. The runtime
setup uses existing dependency manifests and lockfiles. On macOS, install Buf
with `brew install bufbuild/buf/buf`. Start `ollama serve` if needed, then
`ollama pull ministral-3:3b`. Model setup is separate from request measurement.

Prepare the exact source once (run from this implementation checkout):

```sh
git worktree add --detach ../patchgen-source 26304c1ed2f4738676a9607e8fe21e17ebd090f0
```

One command produces and evaluates a new proposal:

```sh
python3 -m patchgen.generator --source ../patchgen-source --output patchgen/evidence/my-run --validate
```

The output directory must be new. The fixture defaults to the saved removal case.
Use `--fixture` for another contract record. `--validate` runs `buf generate`, the
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
After passing validation, `validated.patch` also includes regenerated bindings.
Model usefulness is assessed separately from offline harness correctness.

Offline reference verification (does not call a model):

```sh
python3 -m patchgen.generator --source ../patchgen-source --response patchgen/reference/entity-name-removal/response.json --output patchgen/evidence/offline-reference --validate
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
