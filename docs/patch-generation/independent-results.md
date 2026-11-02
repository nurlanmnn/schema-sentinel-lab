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

## Role-constrained rename continuation — 1 November 2026

A bounded rename proposal now passes the independent pipeline without replaying
an answer: `pipeline-rename-deterministic-002` detects the schema rename, locates
6/6 known sites with no extras, derives syntax-token replacements from descriptors
and recognized roles, then passes the existing validation. This is deterministic
proposal construction with zero model requests, **not a live model success**.
Receiver identity remains unproved and every candidate is proposed for rename;
this result applies to the pinned small testbed, not arbitrary programs.

| Evidence directory | Mode | Actual result |
| --- | --- | --- |
| pipeline-rename-roles-live-001 | prompt 2.7 launch | Host NameError before inference; raw traceback retained |
| pipeline-rename-roles-live-002 | live prompt 2.7 | Rejected Python missing observation-key token and TypeScript candidate review/edit mismatch; no runtime validation |
| pipeline-rename-deterministic-001 | deterministic proposal | Host evidence-directory creation error; no runtime validation |
| pipeline-rename-deterministic-002 | deterministic proposal | Validation passed; no model or reference-response use |

The launch and directory errors were corrected in host code and new directories
were used; no saved response was changed. The stricter live gate prevents the
omitted Python observation key from reaching compilation, where the earlier 2.6
attempt had not detected it. C# passed the 2.7 mechanical check; the complete live
proposal still failed. No automatic feedback repair or fallback was used.

The deterministic result passes Buf regeneration, TypeScript/.NET builds,
11 existing unit tests, four original three-service round trips, four independent
v1 payloads, six standalone v1/v2 samples, Python v2 value checks and invalid-version
rejection. The same pinned evaluator-owned test migration is applied separately;
this is not generated test migration. See its `proposal/validated.patch` for the
complete human-review bundle, including bindings and trusted test changes.

The current suite passes **66 tests** (`rename-roles-tests.log`), including negative
role/completeness tests, production request/assembly wiring with a mocked service,
and deterministic proposal isolation from model calls/caller-added answer fields.
These are software tests, not additional realistic benchmark cases. Role constraints
and all-token coverage are recorded in decision 0006. Type migration, active enum
consumers, twenty cases, human baseline, pub/sub, CI and a review UI remain open.

## Bounded UTF-8 type migration — 2 November 2026

`pipeline-type-deterministic-001` passes the independent detector/locator/adapter
and validator with `deterministic_utf8_v2` (`host-utf8/1.0`). It finds 6/6 known
sites plus the same three unchanged v1 candidates. All six required construction/
observation expressions are migrated; the three v1 candidates are explicitly
preserved. This is a deterministic proposal with zero model requests and no
reference-response replay. Earlier live type failures remain unchanged.

Passing checks include Buf regeneration, TypeScript/.NET compilation, 11 existing
unit tests, four original v1 relay round trips, four independent v1 payloads,
six standalone v1/v2 samples, Python v2 text/invalid-version checks and four valid
UTF-8 v2 payloads decoded/reencoded in each of Python, TypeScript and C#.
The UTF-8 policy is explicit and syntax support is testbed-specific; this does
not demonstrate general semantic migration or invalid-byte interoperability.
Human approval is pending. `proposal/validated.patch` is the review bundle.

The current suite passes 71 software tests (`type-utf8-tests-001.log`), adding
wrong-type/binding rejection, unresolved candidate rejection, v1 preservation
and no-model/no-reference construction checks. No new realistic schema-change
case or human baseline is counted. The remaining MVP work includes review UX,
benchmark expansion, active enum consumers, pub/sub and CI.

## Portable human-review interface — 2 November 2026

A local review interface now displays complete patches, intended behavior,
source revision, proposal mode, validation status and retained evidence links.
SHA-256 manifests tie exported decision records to the evidence. Failed validation
disables approval. The CLI rejects changed artifacts/manifests and incomplete
reviewer acknowledgements. Records are self-reported, not authenticated signatures;
no code application or merge exists. Real human approval is still pending.

`pipeline-type-review-001` passes the full type pipeline and exports
`review-type-integrated-001` in one command. Browser checks of `review-type-001`
and `review-rejected-001` confirm required fields and failed-approval gating.
A synthetic rejection downloaded through the UI verifies via the CLI; its
reviewer is explicitly AUTOMATED UI TEST and it is not a human project decision.
Normal and narrow layouts were inspected. A one-pixel fractional viewport rounding
difference at the narrow test size is not content overflow; patch lines scroll
inside their diff panel. Full suite: 82 tests (`review-tests-002.log`).

The review page closes the local presentation gap; authenticated collaboration,
automatic acceptance, benchmark breadth, human timing, active enum handling,
pub/sub and CI remain separate milestones. See decision 0008 and review.md.
