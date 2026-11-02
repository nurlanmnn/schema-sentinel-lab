# 0017: Explicit telemetry m/s to km/h migration

Promote the authored speed-units domain scenario into the buildable testbed,
pinned to `665e06e`. Canonical float32 field 2 changes speed_mps -> speed_kph.
The detector only classifies the structural field rename; it does not discover
unit meaning. The request must explicitly supply factor 3.6, strict threshold
>108.0, speed_kph observations, and exact decoded float32 JSON numbers. Without
any of those decisions the bounded policy rejects. This is supplied semantic
policy, not inferred conversion or general semantic change classification.

Keep the external sample request in meters/second. Tree-sitter recognizes the
same conservative direct construction/observation/predicate shapes as the
precision policy. Descriptor-derived name edits rename the field and observation
keys; AST expression edits multiply producers by 3.6 before float32 serialization
and change the threshold to >108.0. The adopted C# constructor computes in double
before the float cast. Unknown source/receiver shapes and changed predicates
reject. Receiver/data-flow resolution remains bounded to the adopted shapes.

A real failure in `pipeline-telemetry-units-001` exposed JSON float formatting:
C# boxed float32 rendered 106.2 while Python/TS exposed the exact decoded value
106.19999694824219. The evaluator refused to equate those JSON numbers. The policy
now explicitly promotes the decoded C# float to double before JSON serialization,
preserving its exact wire value without inventing precision. The original failed
run and its ineligible review remain retained. This finding also limits the old
float32 baseline: its eight exactly representable values had not exercised this
formatting difference. It does not establish arbitrary-float baseline conformance.

`pipeline-telemetry-units-002` passes 24 real runtime/case checks plus the existing
Entity checks, exporting `review-telemetry-units-002`. The host oracle independently
encodes scaled float32 wire bytes, quantizes expected decoded values and checks
producer bytes, canonical keys and original speeding decisions. It does not
import generated bindings or reference answers. Detector/locator measurement is
9/9 authored lines, no extras, for this small source. Confidence zero is unestimated.

`telemetry-units-reference-001` separately passes the known-correct answer as
offline replay. `telemetry-units-threshold-negative-001` retains Python's old >30
predicate after scaling: it compiles and passes Entity checks, then fails the
below-threshold case. Its review disallows approval. `demo-telemetry-units-001`
passes the complete launcher path. Portable review requires the units-policy
snapshot, shared shape-validator snapshot and all telemetry evidence.

The finite cases do not prove preservation for arbitrary float32 rounding near
boundaries. Same-number changes of meaning require coordinated rollout; mixed
units, mixed versions and telemetry pub/sub are outside this slice. Historical
analysis-only corpus inputs and metrics remain unchanged. This is the third
distinct buildable telemetry migration, not twenty cases or three model successes.
No real human decision, team merge or deployment has occurred.
