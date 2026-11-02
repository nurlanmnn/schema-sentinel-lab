# 0016: Bounded telemetry float64 migration

Promote a second distinct telemetry change into the buildable path: canonical
VehicleTelemetry.speed_mps field 2 widens from float32 to float64. Fixture source
is exactly `665e06e`; observation names, meters/second and strict >30 threshold
are unchanged. The wire type changes fixed32 -> fixed64, so coordinated rollout
is required. This work does not make mixed-version delivery safe.

The deterministic policy requires the descriptor-confirmed singular field change
and an explicit units/threshold preservation instruction. Tree-sitter recognizes
the adopted import/decode bindings and all three construction/observation/threshold
candidate lines in each language. It rejects optional/repeated/oneof/other types,
changed predicates, unknown bindings, incomplete candidates and C# input narrowed
to float. Python float and TS number already hold binary64; their source stays
unchanged and regenerated bindings widen serialization. C# request.Speed is double;
remove the explicit float32 cast at the constructor. No model/reference answer
is consulted and confidence zero remains unestimated. These exact adopted shapes
are a conservative policy, not general type, receiver or data-flow resolution.

The host evaluator independently hand-encodes eleven fixed64 inputs. In addition
to the prior eight cases it includes 30.0000001, 29.9999999 and 16777217.25, which
exercise precision beyond float32 and the strict boundary. All three consumers
must return exact numeric observations/keys and correct speeding results, and all
producers must emit the independently expected bytes: 33 runtime/case checks.
The existing Entity checks still run. The pinned trusted profile allows no tests
to be edited. Portable review requires complete evaluator/process evidence and
also requires the precision-policy snapshot hash for this deterministic strategy.

`pipeline-telemetry-precision-003` passes those checks and exports
`review-telemetry-precision-003`. The first run built successfully but failed on a
missing precision CLI selection; the second caught an incorrect expected oracle
observation key. Both are retained failed evaluator wiring attempts, not runtime
or policy successes. Detection/locator measurement recovers 9/9 authored sites,
no extras, on this one small case. No human approval, team merge or deployment.

`telemetry-precision-reference-001` passes the independently authored known answer
as offline replay, not a model success. `telemetry-precision-narrowing-negative-001`
keeps the C# float cast: regeneration/builds/Entity checks pass, Python/TS pass all
11 precision cases, then C# producer bytes fail at case 8 (30.0000001). Its review
is ineligible. `demo-telemetry-precision-001` passes the complete launcher path.
Final suites: 119 patchgen tests and 23 testbed tests pass. No human decision.
