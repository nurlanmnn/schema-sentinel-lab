# Decision 0003: bounded benchmark seed and explicit producer boundary

Date: 28 October 2026
Status: local implementation for human review

Add three separate schema-change cases without changing the evaluated removal
fixture or teammate components. Define UTF-8-only semantics for the v2 string-to-
bytes change. An unused enum value addition legitimately requires no runtime
patch. Preserve exact source identities and independent expectations. Prompt 2.4
supports general migrations; prompt 2.3 remains available for removal replay.
Each live case gets one request per supplied file and no feedback repair loop.

Keep runtime generation separate from evaluator-owned test migrations and
independent reference patches. Reference replays assess the harness, never model
success. The seeded enum commit is reproducible from its exact parent, schema
blob, fixed author metadata and message. It is not a merged architecture change.

Add adapter 1.0 for structured producer records. Fail on stale identities,
missing/ambiguous input and partial output. Keep producer provenance outside the
prompt. Validate recall separately; a producer's completeness assertion is not
proof. The current prototype measurement is 2/6 known sites, with C# parser failure
and stale descriptor artifacts, so only fixture-fed adapter wiring is accepted
technically. Real integration remains blocked on owner changes and human review.

See the benchmark report and adapter documentation for per-case failures,
acceptance criteria, tests, measurements and next gates. Human approval remains
required even for technically passing bundles. No automatic merge is introduced.
