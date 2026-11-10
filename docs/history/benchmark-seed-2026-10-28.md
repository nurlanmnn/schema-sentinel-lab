# Three-case benchmark seed — 28 October 2026

One additive enum case passed live local validation with no runtime edits.
The rename and type-change model proposals failed. Independently authored
reference patches for both failed cases passed, checking the evaluator separately
from model usefulness. Together with the earlier removal example, this is four
small schema-change cases, not the required twenty-case benchmark or team acceptance.

| Case / evidence directory | Live result | Offline reference result |
| --- | --- | --- |
| `entity-name-rename` / `benchmark-rename-001` | Failed Python syntax: unexpected indentation at migrated standalone assignment; stopped before regeneration/builds | `reference-rename-001`: passed |
| `v2-identifier-bytes` / `benchmark-type-001` | Regenerated bindings; failed TypeScript compilation because TextEncoder/TextDecoder methods were used without instances | `reference-type-001`: passed |
| Corrected type inventory / `benchmark-type-002` | Failed the same TypeScript instance-method compilation checks; no response repair | Same schema/runtime reference was already validated |
| `unused-enum-addition` / `benchmark-enum-001` | Passed: all three model responses were `no_change`; host schema/bindings change only | Not needed to establish runtime migration |

No model response was corrected, and no automatic retry or repair loop ran.
A separately identified second type trial corrects the required-site inventory;
both configurations are retained. Offline reference answers are separate
artifacts, never model responses or model successes. The existing live-001 through
live-007 and review-001 evidence is unchanged. Successful field-removal generation
remains runtime-only, using an independent trusted test migration; model-generated
test migration still has no passing result.

## Exact inputs and semantics

Rename and type cases use source `26304c1ed2f4738676a9607e8fe21e17ebd090f0`.
Rename changes v1 `name` to `display_name` on wire field 2, preserving text and
changing the decoded observation key. Its independent test migration is pinned
by source, schema and patch hashes; it is excluded from all model requests.

Type change affects v2 `entity_id` only: string to bytes, with explicitly defined
UTF-8 construction and textual observations. v1 and the v1 HTTP relay remain
unchanged. Arbitrary non-UTF-8 bytes, mixed-version compatibility, invalid byte
policy and numeric/units conversions are outside this case. Those require a
separate decision before generation. The initial type trial erroneously included two unchanged sites (Python line 50,
C# line 15) as required. Because prompt coverage would force unnecessary edits,
the current fixture removes them and matches the six independently enumerated
required sites. The original input remains in benchmark-type-001/input.json.
benchmark-type-002 is a separate experiment with this corrected inventory,
without editing or repairing any response. A test prevents this mismatch from
returning. The current one-command runner uses the corrected fixture.

Enum source `d573c55e0d157f6b8c909df81b189aadd9040c1b` is a deterministic child of
that testbed commit with one unused top-level Status enum added to the canonical
v1 schema. The benchmark adds STATUS_SUSPENDED = 2. It does not add an Entity field
or exercise active enum consumers. The seed retains old generated files; validation
regenerates bindings. `benchmark-seed.json` and `benchmark.prepare_enum_seed`
recreate and verify the exact commit on a fresh checkout. The evaluated source is
never silently moved to main.

Fixtures, expected classifications, exact required impact sites, trusted test
migration and independent reference patches live under `patchgen/fixtures/` and
`patchgen/reference/`. Model prompt assembly only allowlists schema, behavior,
source and candidate positions; it cannot read the references or evaluator.
Classification labels here are supplied expectations, not measured detector accuracy.

## Reproduce

Use the tools and local installed model from README.md. The exact testbed commit
must exist locally (remote testbed branch `origin/codex/SS-19-SS-20-SS-34-testbed`).
No additional model download is needed on this machine. From the implementation
checkout, with ports 8000–8002 free:

```sh
python3 -m patchgen.benchmark --output patchgen/evidence/benchmark-next
```

This creates a new directory, makes three requests per case with
`ministral-3:8b`, prompt 2.4, temperature 0, seed 42, context 16384 and output
limit 8192, and runs cases sequentially. Failed cases do not skip later ones.
A summary and each request, response, implementation snapshot, rejection, patch,
measurement and validation log are retained. Nonzero exit means at least one
case failed; rerunning requires a new output directory. The orchestration and
exact seed reconstruction have focused tests; the recorded live cases below
were invoked individually using these same generator arguments.

For independent offline checks, add `--references`. This replays only the two
reference patches and labels the unused-enum reference as not run. It is not a
live generation result. All proposals remain review-only in detached workspaces.
The public aggregate outcome for the additive case is `patch` because the host
copies the supplied schema even though each runtime response says `no_change`.

## Checks and measurements

Passing enum and offline-reference runs completed configured `buf generate`,
TypeScript/.NET builds, 11 existing unit tests, four existing three-service round
trips, four additional independent v1 payload cases (normal, empty, Unicode,
escaped), six standalone v1/v2 samples, and invalid Python version rejection.
The offline type reference additionally decoded and reencoded four valid UTF-8
v2 payloads independently in Python, TypeScript and C#, checking bytes and textual
observations. The C# evaluator invokes the compiled local processor through a
separate reflection probe, preserving the proposed runtime source. None of this
is CI, a pub/sub demo, mixed-version acceptance or human approval.

| Live run | Request seconds (Python / TypeScript / C#) | Prepared workflow seconds |
| --- | --- | --- |
| Rename | 36.552 / 29.559 / 29.986 | 97.160 |
| Type | 39.712 / 31.800 / 35.029 | 115.871 |
| Corrected type inventory | 40.177 / 31.123 / 29.464 | 109.389 |
| Enum | 36.073 / 31.063 / 31.110 | 117.089 |

These are individual prepared local attempts on the same M4/16 GiB and existing
Ollama 0.30.8 / Ministral 3 8B digest recorded in each run. Timing includes local
inference/loading and command overhead; it is not a manual/human baseline or
schema-propagation performance. Confidence remains subjective and uncalibrated.
There is no useful general success-rate estimate from three selected cases
or from four attempts with a corrected fixture. The final generator/adapter/
benchmark suite passes 37 tests; see benchmark-summary-001/generator-tests.log.

## Acceptance and next gates

The bounded seed is delivered when exact inputs and separate expectations exist,
all three live attempts are retained, feasible independent validation runs and a
one-command rerun are available, and failures are reported by case. These gates
are met. Technical success for a runtime-generating case requires all validation
to pass; rename and type do not meet that gate. A future prompt/model improvement
must be a new experiment, retain these failures, and avoid feedback repair hidden
inside a first-attempt metric.

Human review must accept schema semantics, impact inventories and complete
validated bundles separately. Team benchmark format alignment (SS-21/SS-22),
expansion to twenty cases, a measured human baseline, active enum semantics,
CI and real detector/locator integration remain open. No push, merge, deployment,
paid compute or automatic repair was performed.
