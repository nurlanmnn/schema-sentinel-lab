# Live model patch evaluation

Model: ministral-3:8b (`1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71`).
Validated proposals: 0/6. Human approval pending.

| Migration | Outcome | Model requests | Generation seconds | Pipeline seconds |
| --- | --- | ---: | ---: | ---: |
| pubsub-rename | compilation | 3 | 170.32 | 177.54 |
| pubsub-removal | file_contract_or_generation_rejected | 3 | 164.31 | 165.81 |
| pubsub-utf8 | file_contract_or_generation_rejected | 3 | 167.75 | 169.89 |
| telemetry-rename | file_contract_or_generation_rejected | 3 | 98.49 | 100.43 |
| telemetry-precision | file_contract_or_generation_rejected | 3 | 116.69 | 119.09 |
| telemetry-units | independent_telemetry_semantics | 3 | 126.81 | 139.02 |

Generation includes local loading/inference wall time; pipeline includes independent analysis and validation.
Contract/generation rejections do not establish compilation or runtime behavior. Deterministic and reference replays are excluded.
This small single-trial suite is not a broad model comparison, twenty-case benchmark or human review baseline.

## Request timing

These are serving counters, not a controlled cold/warm comparison. Missing counters remain unknown.

| Migration/request | File | Contract | Load s | Prompt s | Decode s | Output tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| pubsub-rename/01 | runtimes/csharp/main.cs | passed | 14.27 | 23.15 | 34.12 | 493 |
| pubsub-rename/02 | runtimes/python/main.py | passed | 0.13 | 23.76 | 25.78 | 373 |
| pubsub-rename/03 | runtimes/typescript/main.ts | passed | 0.14 | 19.74 | 28.58 | 413 |
| pubsub-removal/01 | runtimes/csharp/main.cs | passed | 0.15 | 22.35 | 31.31 | 427 |
| pubsub-removal/02 | runtimes/python/main.py | failed | 0.15 | 25.16 | 36.09 | 573 |
| pubsub-removal/03 | runtimes/typescript/main.ts | passed | 0.16 | 19.71 | 28.20 | 456 |
| pubsub-utf8/01 | runtimes/csharp/main.cs | failed | 0.17 | 23.07 | 39.28 | 625 |
| pubsub-utf8/02 | runtimes/python/main.py | passed | 0.14 | 23.26 | 25.95 | 436 |
| pubsub-utf8/03 | runtimes/typescript/main.ts | passed | 0.15 | 19.63 | 35.11 | 581 |
| telemetry-rename/01 | runtimes/csharp/Telemetry.cs | failed | 0.19 | 8.13 | 26.28 | 456 |
| telemetry-rename/02 | runtimes/python/telemetry_runtime.py | failed | 0.16 | 5.93 | 23.07 | 405 |
| telemetry-rename/03 | runtimes/typescript/telemetry.ts | passed | 0.14 | 5.93 | 28.04 | 498 |
| telemetry-precision/01 | runtimes/csharp/Telemetry.cs | passed | 0.18 | 8.41 | 32.18 | 559 |
| telemetry-precision/02 | runtimes/python/telemetry_runtime.py | passed | 0.14 | 6.19 | 28.89 | 512 |
| telemetry-precision/03 | runtimes/typescript/telemetry.ts | failed | 0.15 | 5.93 | 34.17 | 597 |
| telemetry-units/01 | runtimes/csharp/Telemetry.cs | passed | 0.14 | 8.25 | 34.54 | 595 |
| telemetry-units/02 | runtimes/python/telemetry_runtime.py | passed | 0.16 | 5.87 | 33.73 | 589 |
| telemetry-units/03 | runtimes/typescript/telemetry.ts | passed | 0.15 | 5.75 | 37.63 | 645 |

## pubsub-rename rejection evidence

- main.ts(82,5): error TS1128: Declaration or statement expected.
- main.ts(83,5): error TS1128: Declaration or statement expected.

## pubsub-removal rejection evidence

- Request 02: invalid/duplicate candidate review line

## pubsub-utf8 rejection evidence

- Request 01: candidate decision/edit coverage mismatch

## telemetry-rename rejection evidence

- Request 01: missing candidate reviews
- Request 02: missing candidate reviews

## telemetry-precision rejection evidence

- Request 03: overlapping line edit ranges
