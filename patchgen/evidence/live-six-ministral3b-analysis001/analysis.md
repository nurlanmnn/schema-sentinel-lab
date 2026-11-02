# Live model patch evaluation

Model: ministral-3:3b (`f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d`).
Validated proposals: 0/6. Human approval pending.

| Migration | Outcome | Model requests | Generation seconds | Pipeline seconds |
| --- | --- | ---: | ---: | ---: |
| pubsub-rename | file_contract_or_generation_rejected | 3 | 65.78 | 67.13 |
| pubsub-removal | file_contract_or_generation_rejected | 3 | 64.50 | 65.73 |
| pubsub-utf8 | file_contract_or_generation_rejected | 3 | 70.24 | 71.41 |
| telemetry-rename | file_contract_or_generation_rejected | 3 | 43.22 | 44.62 |
| telemetry-precision | file_contract_or_generation_rejected | 3 | 48.26 | 49.60 |
| telemetry-units | file_contract_or_generation_rejected | 3 | 44.12 | 45.73 |

Generation includes local loading/inference wall time; pipeline includes independent analysis and validation.
Contract/generation rejections do not establish compilation or runtime behavior. Deterministic and reference replays are excluded.
This small single-trial suite is not a broad model comparison, twenty-case benchmark or human review baseline.

## Request timing

These are serving counters, not a controlled cold/warm comparison. Missing counters remain unknown.

| Migration/request | File | Contract | Load s | Prompt s | Decode s | Output tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| pubsub-rename/01 | runtimes/csharp/main.cs | failed | 3.32 | 10.81 | 13.15 | 437 |
| pubsub-rename/02 | runtimes/python/main.py | passed | 0.11 | 10.44 | 9.87 | 322 |
| pubsub-rename/03 | runtimes/typescript/main.ts | passed | 0.11 | 8.81 | 8.93 | 299 |
| pubsub-removal/01 | runtimes/csharp/main.cs | failed | 0.15 | 10.03 | 14.18 | 465 |
| pubsub-removal/02 | runtimes/python/main.py | passed | 0.11 | 10.46 | 9.43 | 308 |
| pubsub-removal/03 | runtimes/typescript/main.ts | passed | 0.12 | 8.84 | 10.50 | 350 |
| pubsub-utf8/01 | runtimes/csharp/main.cs | failed | 0.15 | 10.31 | 13.55 | 442 |
| pubsub-utf8/02 | runtimes/python/main.py | passed | 0.11 | 10.47 | 10.47 | 332 |
| pubsub-utf8/03 | runtimes/typescript/main.ts | failed | 0.13 | 8.95 | 15.49 | 505 |
| telemetry-rename/01 | runtimes/csharp/Telemetry.cs | passed | 0.15 | 3.62 | 13.69 | 467 |
| telemetry-rename/02 | runtimes/python/telemetry_runtime.py | passed | 0.13 | 2.61 | 11.57 | 415 |
| telemetry-rename/03 | runtimes/typescript/telemetry.ts | failed | 0.13 | 2.62 | 8.35 | 307 |
| telemetry-precision/01 | runtimes/csharp/Telemetry.cs | failed | 0.15 | 3.68 | 15.78 | 548 |
| telemetry-precision/02 | runtimes/python/telemetry_runtime.py | passed | 0.11 | 2.65 | 11.33 | 414 |
| telemetry-precision/03 | runtimes/typescript/telemetry.ts | passed | 0.11 | 2.61 | 11.54 | 423 |
| telemetry-units/01 | runtimes/csharp/Telemetry.cs | passed | 0.16 | 3.60 | 13.23 | 460 |
| telemetry-units/02 | runtimes/python/telemetry_runtime.py | passed | 0.11 | 2.62 | 12.54 | 452 |
| telemetry-units/03 | runtimes/typescript/telemetry.ts | failed | 0.12 | 2.61 | 8.83 | 323 |

## pubsub-rename rejection evidence

- Request 01: invalid/duplicate candidate review line

## pubsub-removal rejection evidence

- Request 01: invalid/duplicate candidate review line

## pubsub-utf8 rejection evidence

- Request 01: missing candidate reviews
- Request 03: invalid/duplicate candidate review line

## telemetry-rename rejection evidence

- Request 03: missing candidate reviews

## telemetry-precision rejection evidence

- Request 01: candidate decision/edit coverage mismatch

## telemetry-units rejection evidence

- Request 03: missing candidate reviews
