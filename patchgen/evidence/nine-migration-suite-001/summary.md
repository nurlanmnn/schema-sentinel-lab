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
| inventory-stock-release | validation_passed | true | 4/4 | 2 | [log](inventory-stock-release.log), [review](inventory-stock-release/review/index.html) |

All planned cases remain in completed-suite denominators. Missing measurements count as zero matched sites and incorrect classification.

Timings include bootstrap and prepared-fixture work. Live model performance and human review time are unmeasured.
These are small authored migrations, not the twenty-case MVP benchmark. Structural classification does not infer units.

[Machine-readable summary](summary.json) · [Pinned manifest](manifest.json)
