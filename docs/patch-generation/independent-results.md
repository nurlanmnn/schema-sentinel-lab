# Independent pipeline evidence — 1 November 2026

Detector/locator/adapter measurements against exact testbed commit
`26304c1ed2f4738676a9607e8fe21e17ebd090f0`:

| Schema pair | Structural classification | Known sites | Extra candidates |
| --- | --- | --- | --- |
| v1 name removal | field_removed, correct | 6/6 | 0 |
| v1 name → display_name | field_renamed, correct | 6/6 | 0 |
| v2 entity_id string → bytes | field_type_changed, correct | 6/6 | 3 |

Evidence: `pipeline-final-removal`, `pipeline-final-rename`, `pipeline-final-type`
under `patchgen/evidence/`. These recover pre-existing inventories independently;
none supplies target positions to the producer. The known type extras belong to
unchanged v1 code. 18/18 known sites across three related cases is not a general
recall claim or proof that the inventories exhaust every possible site.

The exact enum seed was recreated with `benchmark.prepare_enum_seed()` at
`d573c55e0d157f6b8c909df81b189aadd9040c1b`. `pipeline-enum-001` correctly detects
`enum_value_added` but rejects locator integration because active enum consumer
analysis is unsupported. It is not a no-change validation success.

The suite passes 59 tests, including real three-case descriptor/parser/adapter
integration, nested-message wire identity, unsupported metadata, parser errors,
reflection, construction/casts/naming, candidate reviews and rename token bounds.
See `pipeline-tests.log`. These are not 59 realistic benchmark cases.

## Generator and validation outcomes

| Evidence directory | Mode / strategy | Result |
| --- | --- | --- |
| pipeline-rename-live-001 | live requested, prompt 2.5 | Ollama stopped; failed before model requests |
| pipeline-rename-live-002 | live, prompt 2.5 line edits | Rejected duplicate/invalid TypeScript candidate review; Python response also has incorrect indentation/old attribute read |
| pipeline-type-live-001 | live, prompt 2.5 line edits | Rejected C#/TypeScript candidate decision/edit coverage mismatch; response also confuses v1/v2 code |
| pipeline-rename-token-live-001 | live, prompt 2.6 syntax tokens | Mechanical checks passed; Buf regeneration passed; TypeScript build failed because construction used display_name instead of displayName; Python observation-key token was also omitted |
| pipeline-rename-reference-001 | offline reference replay, real detector/locator input | Validation passed |

The narrower token strategy preserves layout and prevents arbitrary replacement
source, but it does not resolve naming roles or ensure every necessary token was
selected. The failed compile stopped the token attempt before runtime oracles;
the omitted Python key was found by response inspection, not a passing runtime
check. Do not treat these new live attempts as successes or quietly repair them.
Earlier 2.3/2.4 attempts remain intact. No automatic feedback repair was used.
Confidence values remain subjective; high model confidence did not predict success.

The offline rename replay passed configured Buf regeneration, TS/.NET builds,
11 existing unit tests, four original round trips, four independent v1 payloads,
six standalone v1/v2 samples, additional Python v2 values and invalid-version
rejection. Its separately pinned evaluator test migration never entered model
requests. This verifies detector/locator-to-adapter-to-validator wiring using a
known-correct proposal; it does not establish live model usefulness or model-
generated test migration. Human approval remains required.

Intermediate tooling evidence is retained: `pipeline-removal-002` reached a
measurement-reader mismatch with the older removal reference format. The reader
was corrected, integration-tested, and rerun as `pipeline-removal-003`.
`pipeline-removal-001` precedes the measurement mapping correction.

The implementation is in the personal private repository `nurlanmnn/schema-sentinel-lab`,
branch `codex/independent-pipeline`, with inherited attribution/history intact.
The team upstream remains fetch-only with push URL DISABLED. Original checkouts
were read-only verified unchanged. No team push/merge, deployment, CI run, public
release, collaborator invitation or human acceptance is implied. Active enum
consumers, semantic/receiver resolution, a realistic twenty-case benchmark,
manual baseline, pub/sub integration and review UI remain future work.
