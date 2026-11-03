# Live model patch evaluation

Model: ministral-3:14b (`4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7`).
Validated proposals: 0/6. This analysis records no human approval.

| Migration | Outcome | Model requests | Generation seconds | Pipeline seconds |
| --- | --- | ---: | ---: | ---: |
| pubsub-rename | file_contract_or_generation_rejected | 3 | 312.58 | 314.19 |
| pubsub-removal | file_contract_or_generation_rejected | 3 | 357.26 | 368.00 |
| pubsub-utf8 | file_contract_or_generation_rejected | 3 | 279.18 | 383.69 |
| telemetry-rename | compilation | 3 | 189.62 | 406.46 |
| telemetry-precision | file_contract_or_generation_rejected | 3 | 219.89 | 270.71 |
| telemetry-units | compilation | 3 | 192.02 | 270.12 |

Generation includes local loading/inference wall time; pipeline includes independent analysis and validation.
Contract/generation rejections do not establish compilation or runtime behavior. Deterministic and reference replays are excluded.
This small single-trial suite is not a broad model comparison, twenty-case benchmark or human review baseline.

## Request timing

These are serving counters, not a controlled cold/warm comparison. Missing counters remain unknown.

| Migration/request | File | Contract | Load s | Prompt s | Decode s | Output tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| pubsub-rename/01 | runtimes/csharp/main.cs | passed | 15.58 | 38.02 | 40.20 | 397 |
| pubsub-rename/02 | runtimes/python/main.py | failed | 0.49 | 38.79 | 102.08 | 997 |
| pubsub-rename/03 | runtimes/typescript/main.ts | passed | 0.92 | 32.98 | 39.91 | 394 |
| pubsub-removal/01 | runtimes/csharp/main.cs | passed | 0.40 | 36.20 | 40.21 | 394 |
| pubsub-removal/02 | runtimes/python/main.py | failed | 1.33 | 38.54 | 131.37 | 1085 |
| pubsub-removal/03 | runtimes/typescript/main.ts | passed | 1.61 | 33.41 | 63.14 | 382 |
| pubsub-utf8/01 | runtimes/csharp/main.cs | failed | 1.32 | 39.64 | 62.29 | 590 |
| pubsub-utf8/02 | runtimes/python/main.py | passed | 1.22 | 40.35 | 39.17 | 379 |
| pubsub-utf8/03 | runtimes/typescript/main.ts | failed | 1.34 | 32.92 | 54.49 | 529 |
| telemetry-rename/01 | runtimes/csharp/Telemetry.cs | passed | 0.44 | 14.19 | 51.59 | 527 |
| telemetry-rename/02 | runtimes/python/telemetry_runtime.py | passed | 0.76 | 11.00 | 47.41 | 481 |
| telemetry-rename/03 | runtimes/typescript/telemetry.ts | passed | 0.62 | 11.07 | 48.63 | 501 |
| telemetry-precision/01 | runtimes/csharp/Telemetry.cs | passed | 15.99 | 17.52 | 45.85 | 463 |
| telemetry-precision/02 | runtimes/python/telemetry_runtime.py | failed | 0.41 | 11.83 | 54.37 | 522 |
| telemetry-precision/03 | runtimes/typescript/telemetry.ts | failed | 1.16 | 11.56 | 57.64 | 500 |
| telemetry-units/01 | runtimes/csharp/Telemetry.cs | passed | 0.72 | 13.26 | 52.06 | 559 |
| telemetry-units/02 | runtimes/python/telemetry_runtime.py | passed | 0.29 | 10.44 | 53.40 | 567 |
| telemetry-units/03 | runtimes/typescript/telemetry.ts | passed | 0.38 | 10.81 | 47.15 | 512 |

## pubsub-rename rejection evidence

- Request 02: line edit makes no change

## pubsub-removal rejection evidence

- Request 02: line edit makes no change

## pubsub-utf8 rejection evidence

- Request 01: line edit makes no change
- Request 03: candidate decision/edit coverage mismatch

## telemetry-rename rejection evidence

- telemetry.ts(11,39): error TS2339: Property 'speedMps' does not exist on type 'VehicleTelemetry'.

## telemetry-precision rejection evidence

- Request 02: line edit makes no change
- Request 03: candidate decision/edit coverage mismatch

## telemetry-units rejection evidence

- telemetry.ts(9,77): error TS2353: Object literal may only specify known properties, and 'speedMps' does not exist in type 'VehicleTelemetry'.
