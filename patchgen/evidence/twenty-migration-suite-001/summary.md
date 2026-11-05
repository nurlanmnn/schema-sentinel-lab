# Migration evaluation

Status: completed. Deterministic authored cases; human decisions pending.

| Migration | Validation | Structural category correct | Candidate lines | Extras | Evidence |
| --- | --- | --- | --- | --- | --- |
| pubsub-rename | validation_passed | true | 6/6 | 0 | [log](pubsub-rename.log) |
| pubsub-removal | validation_passed | true | 6/6 | 0 | [log](pubsub-removal.log) |
| pubsub-utf8 | validation_passed | true | 6/6 | 3 | [log](pubsub-utf8.log) |
| telemetry-rename | validation_passed | true | 9/9 | 0 | [log](telemetry-rename.log) |
| telemetry-precision | validation_passed | true | 9/9 | 0 | [log](telemetry-precision.log) |
| telemetry-units | validation_passed | true | 9/9 | 0 | [log](telemetry-units.log) |
| inventory-width | validation_passed | true | 9/9 | 2 | [log](inventory-width.log) |
| inventory-zigzag | validation_passed | true | 9/9 | 2 | [log](inventory-zigzag.log) |
| inventory-stock-release | validation_passed | true | 4/4 | 2 | [log](inventory-stock-release.log) |
| inventory-presence | validation_passed | true | 11/11 | 0 | [log](inventory-presence.log) |
| inventory-labels | validation_passed | true | 5/5 | 4 | [log](inventory-labels.log) |
| inventory-reservation | validation_passed | true | 8/8 | 3 | [log](inventory-reservation.log) |
| telemetry-quantized | validation_passed | true | 3/3 | 6 | [log](telemetry-quantized.log) |
| inventory-state-rename | validation_passed | true | 4/4 | 14 | [log](inventory-state-rename.log) |
| telemetry-message-rename | validation_passed | true | 8/8 | 0 | [log](telemetry-message-rename.log) |
| telemetry-tag-move | validation_passed | true | 9/9 | 0 | [log](telemetry-tag-move.log), [review](telemetry-tag-move/review/index.html) |
| telemetry-json-key | validation_passed | true | 3/3 | 6 | [log](telemetry-json-key.log), [review](telemetry-json-key/review/index.html) |
| inventory-packed-bins | validation_passed | true | 6/6 | 3 | [log](inventory-packed-bins.log), [review](inventory-packed-bins/review/index.html) |
| inventory-routing-oneof | validation_passed | true | 9/9 | 2 | [log](inventory-routing-oneof.log), [review](inventory-routing-oneof/review/index.html) |
| inventory-state-retirement | validation_passed | true | 4/4 | 14 | [log](inventory-state-retirement.log), [review](inventory-state-retirement/review/index.html) |

All planned cases remain in completed-suite denominators. Missing measurements count as zero matched sites and incorrect classification.

Timings include bootstrap and prepared-fixture work. Live model performance and human review time are unmeasured.
These are authored migrations in a local testbed. Structural classification does not infer units.

[Machine-readable summary](summary.json) · [Pinned manifest](manifest.json)
