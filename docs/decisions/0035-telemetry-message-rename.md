# 0035. Rename the standalone telemetry message

Rename `VehicleTelemetry` to `GroundSpeedSample`. The pinned proposal
updates imports, decode references and constructors across Python,
TypeScript and C#. Field names and numbers, raw protobuf bytes, JSON
observations and the strict speeding threshold remain stable.

Classification requires one standalone top-level proto3 message and a
descriptor that otherwise matches exactly. The syntax locator finds
generated type candidates. The pinned proposal requires all authored
runtime references. RPC and referenced or nested message renames stay
outside this boundary.

The independent evaluator checks 24 runtime outcomes for raw telemetry.
Generated type APIs change even though raw payloads stay compatible.
Type-name envelopes and reflection-based clients are outside this case.
Human review remains pending.
