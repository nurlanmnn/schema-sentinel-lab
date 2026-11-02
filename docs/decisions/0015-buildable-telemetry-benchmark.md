# 0015: Buildable telemetry benchmark

The domain corpus remains an analysis-only measurement. Add an independently
buildable telemetry runtime to each existing language, using a canonical
`simulation.telemetry.VehicleTelemetry` message. This adapts the snippet domain
into the actual testbed; it does not change historical corpus inputs or counts.
The baseline field is `speed_mps`, float32 wire number 2; the planned rename is
`ground_speed_mps` with unchanged wire number, units and strict >30 threshold.

Each runtime has an explicit `--telemetry` stdin/stdout mode alongside the
Entity relay/subscriber modes. It decodes independently authored bytes and
constructs a generated-binding sample. The host evaluator uses no generated
bindings or reference patch: it hand-encodes eight float32 cases, checks exact
producer bytes, exact observation keys/values and the threshold result. Cases
cover zero, negative, below/equal/above threshold, Unicode/empty IDs and a higher
speed. They are finite authored cases, not arbitrary-wire or units safety.
No network service is started by these telemetry checks.

Initial baseline: `telemetry-baseline-001` and `002` pass 24 runtime/case checks.
They were run in a dirty implementation checkout rooted at commit 0671d35; that
revision alone does not identify the added source. Later evaluator reports also
retain source hashes and dirty status. The initial remote generation failure is
retained in `telemetry-baseline-build-001.log` and `telemetry-buf-retry-001.log`.
The second build regenerated locally and passed the existing Entity checks.
Local code generation is explicit and pinned; see `tools/codegen/README.md`.

This baseline alone is not a generated migration, a model success, human
approval, pub/sub telemetry integration or completion of the twenty-case MVP.
The rename must earn independent proposal, build, behavior and review evidence.
No human decision, merge or team deployment is authorized by passing checks.

## Rename pipeline checkpoint

The fixture is pinned to baseline `32e39a2`. Independent detection classifies the
same-number float field rename; syntax location recovers the nine authored
construction/observation/threshold lines with no extra candidate lines. This
small-case recall does not establish receiver identity or general completeness.
The host rename policy proposes the patch without reading known-correct answers.
Its existing TypeScript observation role now recognizes snake_case keys paired
with descriptor-derived camelCase reads; unrelated value properties and missing
explicit observation policy still reject. Confidence remains an unestimated zero.

`pipeline-telemetry-rename-001` failed on that syntax-role limitation. `002`
passed builds, existing Entity checks and 24 telemetry cases; `003` also retained
local toolchain identity and exported `review-telemetry-rename-001`. The trusted
profile pins source/schema/change and allows no test patch. A host snapshot of
the telemetry evaluator runs against the isolated proposal, never overlaying
runtime code. The complete validated patch includes regenerated bindings.
Review export/verification requires all telemetry outputs and oracle source,
checks its hash and source identity, and rechecks each retained runtime result
against the fixed host cases. Local generation also retains and checks its source
and toolchain record. Portable manifests hash these artifacts. No human decision
has been recorded.

## Real evaluator controls

`demo-telemetry-rename-001` passes the one-command path and review export.
`telemetry-reference-replay-003` passes an evaluator-authored known-correct patch;
this is an offline answer check, not another production or model success.
`telemetry-threshold-negative-003` changes Python's predicate to >=30: generation
and compilation succeed and Entity checks pass, but the telemetry evaluator
rejects case 2 (exactly 30 m/s). Its review bundle explicitly disallows approval.
The first control attempts lacked required git diff headers and the second had a
mistaken doubled TypeScript replacement; all those invalid control artifacts are
retained as failures, not counted as semantic negative-control evidence.
Final suites at this checkpoint: 114 patchgen tests and 23 testbed tests pass.

## Input boundary for precision work

The next baseline makes JSON input precision explicit: C# request.Speed is double
and the float32 sample constructor explicitly narrows with `(float)request.Speed`.
Existing eight-case behavior remains unchanged (24 checks pass in
`telemetry-double-input-baseline-001`). This enables an independently testable
float32-to-float64 migration without silently narrowing JSON input first. It is
baseline infrastructure, not a successful precision migration by itself. The
already pinned rename fixture and retained results remain unchanged.
