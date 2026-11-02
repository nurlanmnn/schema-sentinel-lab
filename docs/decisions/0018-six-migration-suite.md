# 0018: Sequential six-migration evaluation suite

## Decision

`run_benchmark.py` runs the existing six distinct authored policies through the
independent pipeline and portable review export. It uses the pub/sub versions of
Entity rename, removal and UTF-8 identifier migration, plus telemetry rename,
float32-to-float64 precision and explicitly supplied units conversion. Earlier
Entity transport variants, reference replays and negative controls are not extra
migration cases. No new dependencies or model requests are introduced.

Run from a prepared full clone with Python 3.13:

```sh
python3.13 run_benchmark.py --local-codegen --output patchgen/evidence/NEW-suite
```

Local codegen requires the preinstalled pinned tools described in
`tools/codegen/README.md`. Omit the option to use the existing remote Buf path,
which may fail if remote quotas are exhausted. Each demo retains bootstrap,
compilation, oracle and review evidence. Shared-port runtime validation runs
sequentially. Existing outputs are rejected. A failed child remains in the suite,
and later cases still run; interrupted suites retain `status: running` and must
not be interpreted as completed evaluations.

## Measurement contract

The fixed manifest binds fixture and ground-truth hashes to pinned source
revisions and authored structural categories. Existing telemetry expectations
lack embedded identity fields; the suite binds their exact bytes through this
manifest. A conflicting embedded identity is rejected. Ground truth is used for
evaluation after production analysis, never as generator input.

The suite reports six case denominators and 45 expected runtime candidate lines.
Missing or incompatible measurements contribute zero matched sites and incorrect
classification; measurement availability is reported separately. Extra candidate
lines are reported. Classification accuracy concerns structural categories only:
the units case is a structural rename, and the conversion policy comes from the
request. Recall is relative to these small authored inventories, without receiver,
alias or dataflow completeness proof.

Validation counts require successful child exit, demo/pipeline status, expected
deterministic strategy and source identity, passing independent runtime evidence,
and a review HTML artifact. Validated patches remain human-review proposals.
Reports retain child paths and report hashes, runner source/hash, implementation
revision/dirty state, manifest, per-case logs and wall-clock timings. Timings
include environment bootstrap and prepared-fixture work; they do not measure
operational schema propagation or human review time. Model validation rate and
human review time remain null, not zero-valued successes.

## Acceptance criteria

- All six cases execute sequentially and retain success or failure evidence.
- Missing reports and incompatible site counts cannot shrink denominators.
- Passing status text alone cannot count as a validated proposal.
- Existing evidence cannot be overwritten.
- A real suite run records actual runtime and portable-review outcomes.

This is six small deterministic migrations, not the twenty-case MVP benchmark,
not a live LLM evaluation, and not a human manual baseline. Increasing realistic
case diversity and obtaining a measured human baseline remain open work.

## Retained validation

`patchgen/evidence/six-migration-suite-001/summary.json` records the actual full
run: 6/6 structural classifications correct, 45/45 authored candidate lines
matched, three conservative extras in the Entity UTF-8 case, and 6/6 proposals
passing compilation, independent runtime checks and portable review export.
The run took 53.03 seconds including repeated bootstrap. It made zero model
requests and contains no human decisions. The runner records its dirty
implementation state and exact source snapshot; this evidence predates its
commit. Unit checks also exercise missing/incompatible reports, false pass
labels, immutable outputs, conflicting ground-truth identity, and continuation
after all six child launches fail.
