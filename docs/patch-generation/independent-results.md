# Independent pipeline evidence — 1 November 2026

Detector/locator/adapter measurements against exact testbed commit
`26304c1ed2f4738676a9607e8fe21e17ebd090f0`:

| Schema pair | Structural classification | Known sites | Extra candidates |
| --- | --- | --- | --- |
| v1 name removal | field_removed, correct | 6/6 | 0 |
| v1 name → display_name | field_renamed, correct | 6/6 | 0 |
| v2 entity_id string → bytes | field_type_changed, correct | 6/6 | 3 |

Evidence: `pipeline-removal-003`, `pipeline-rename-002`, `pipeline-type-002` under
`patchgen/evidence/`. This is independent recovery of pre-existing inventories;
none supplies target positions to the producer. The known type extras belong to
unchanged v1 code. 18/18 known sites across these three related cases is not a
general recall claim or proof that the inventories contain every possible site.

The exact enum seed was recreated with `benchmark.prepare_enum_seed()` at
`d573c55e0d157f6b8c909df81b189aadd9040c1b`. `pipeline-enum-001` correctly detects
`enum_value_added` but explicitly rejects locator integration because active enum
consumer analysis is unsupported. It is not a no-change validation success.

The suite passes 55 tests, including three-case real descriptor/parser/adapter
integration, nested-message wire identity, unsupported file/JSON metadata,
parse errors, reflection, construction/casts/naming and candidate-review rejection.
See `pipeline-tests.log`. These tests are not 55 realistic benchmark cases.

Live prompt 2.5 evaluation is a new experiment with the installed local
Ministral 3 8B. `pipeline-rename-live-001` failed before model requests because
Ollama was stopped. A separate `pipeline-rename-live-002` was started after the
local server was started; its final result is retained in report.json. Earlier
2.3/2.4 attempts remain intact. Reference replays, when recorded, assess the
harness independently and never count as live model success.

Intermediate tooling evidence is retained: `pipeline-removal-002` reached a
measurement reader mismatch with the older removal reference format. The reader
was corrected, integration-tested, and rerun as `pipeline-removal-003`.
`pipeline-removal-001` precedes the measurement mapping correction.
No team push/merge, deployment or human acceptance is implied.
