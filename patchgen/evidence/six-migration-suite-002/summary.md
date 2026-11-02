# Six-migration evaluation

Status: completed. Deterministic authored cases; human decisions pending.

| Migration | Validation | Structural category correct | Candidate lines | Extras | Evidence |
| --- | --- | --- | --- | --- | --- |
| pubsub-rename | validation_passed | true | 6/6 | 0 | [log](pubsub-rename.log), [review](pubsub-rename/review/index.html) |
| pubsub-removal | validation_passed | true | 6/6 | 0 | [log](pubsub-removal.log), [review](pubsub-removal/review/index.html) |
| pubsub-utf8 | validation_passed | true | 6/6 | 3 | [log](pubsub-utf8.log), [review](pubsub-utf8/review/index.html) |
| telemetry-rename | validation_passed | true | 9/9 | 0 | [log](telemetry-rename.log), [review](telemetry-rename/review/index.html) |
| telemetry-precision | validation_passed | true | 9/9 | 0 | [log](telemetry-precision.log), [review](telemetry-precision/review/index.html) |
| telemetry-units | validation_passed | true | 9/9 | 0 | [log](telemetry-units.log), [review](telemetry-units/review/index.html) |

All six cases remain in completed-suite denominators. Missing measurements count as zero matched sites and incorrect classification.

Timings include bootstrap and prepared-fixture work. Live model performance and human review time are unmeasured.
This is six small authored migrations, not the twenty-case MVP benchmark. Structural classification does not infer units.

[Machine-readable summary](summary.json) · [Pinned manifest](manifest.json)
