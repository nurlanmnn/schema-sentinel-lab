# 0033. Quantize telemetry speed to integer meters per second

The pinned migration changes telemetry field 2 from float32 to int32.
For finite JSON producer inputs, clamp to the signed int32 bounds and
truncate toward zero. Consumer observations keep the `speed_mps` key
and expose an integer. The strict speeding threshold still compares
the decoded value to 30. Quantization can change the decision for
fractional inputs between 30 and 31.

The existing type detector and locator identify the change and the three
producer edits. The observations and predicate already read the generated
field directly. The deterministic proposal requires its pinned source,
the exact descriptor event, and the explicit conversion policy.

The independent evaluator supplies varint consumer payloads and separately
specifies expected producer bytes for fractional, signed, threshold, and
overflow inputs. It checks 36 outcomes across Python, TypeScript, and C#.

Field 2 changes from fixed32 to varint wire encoding. Old and new
decoders can skip each other's speed value and observe the default.
Coordinate writers and readers across the migration. Human review
remains pending.
