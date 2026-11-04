# Migration evaluation

Status: completed. Deterministic authored cases; human decisions pending.

| Migration | Validation | Structural category correct | Candidate lines | Extras | Evidence |
| --- | --- | --- | --- | --- | --- |
| pubsub-rename | validation_passed | true | 6/6 | 0 | [log](pubsub-rename.log), [review](pubsub-rename/review/index.html) |
| pubsub-removal | validation_passed | true | 6/6 | 0 | [log](pubsub-removal.log), [review](pubsub-removal/review/index.html) |
| pubsub-utf8 | validation_passed | true | 6/6 | 3 | [log](pubsub-utf8.log), [review](pubsub-utf8/review/index.html) |
| telemetry-rename | validation_passed | true | 9/9 | 0 | [log](telemetry-rename.log), [review](telemetry-rename/review/index.html) |
| telemetry-precision | validation_passed | true | 9/9 | 0 | [log](telemetry-precision.log), [review](telemetry-precision/review/index.html) |
| telemetry-units | validation_passed | true | 9/9 | 0 | [log](telemetry-units.log), [review](telemetry-units/review/index.html) |
| inventory-width | validation_passed | true | 9/9 | 2 | [log](inventory-width.log), [review](inventory-width/review/index.html) |
| inventory-zigzag | validation_passed | true | 9/9 | 2 | [log](inventory-zigzag.log), [review](inventory-zigzag/review/index.html) |
| inventory-stock-release | validation_passed | true | 4/4 | 2 | [log](inventory-stock-release.log), [review](inventory-stock-release/review/index.html) |
| inventory-presence | validation_passed | true | 11/11 | 0 | [log](inventory-presence.log), [review](inventory-presence/review/index.html) |
| inventory-labels | validation_passed | true | 5/5 | 4 | [log](inventory-labels.log), [review](inventory-labels/review/index.html) |
| inventory-reservation | validation_passed | true | 8/8 | 3 | [log](inventory-reservation.log), [review](inventory-reservation/review/index.html) |

All planned cases remain in completed-suite denominators. Missing measurements count as zero matched sites and incorrect classification.

Timings include bootstrap and prepared-fixture work. Live model performance and human review time are unmeasured.
These are small authored migrations, not the twenty-case MVP benchmark. Structural classification does not infer units.

[Machine-readable summary](summary.json) · [Pinned manifest](manifest.json)
