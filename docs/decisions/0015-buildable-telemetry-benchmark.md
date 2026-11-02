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
