# Initial NVIDIA Nemotron trial

Model: `nvidia/nemotron-3-ultra-550b-a55b`, direct NVIDIA API.

Two preselected cases, six actual requests, no automatic retries or repair.
One validated patch out of two. This small selected trial is not a full benchmark success rate.

- pubsub-rename: passed compilation, existing tests and actual local pub/sub across Python, TypeScript and C#; 24 decoded deliveries.
- telemetry-units: compiled, then failed the exact observation contract. C# serialized the decoded float32 as 106.2; expected and Python/TypeScript observations were 106.19999694824219. Wire conversion and threshold edits were present. Patch remains rejected.

Total provider-reported tokens: 22783. Request wall time: 35.81 seconds. Neither figure measures human review or full schema propagation.

Every passing proposal still requires human approval. No merge occurred.
The implementation was uncommitted during this trial; implementation snapshots and transport hashes are retained.
