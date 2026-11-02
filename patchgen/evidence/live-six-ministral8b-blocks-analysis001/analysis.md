# Live model patch evaluation

Model: ministral-3:8b (`1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71`).
Validated proposals: 0/6. Human approval pending.

| Migration | Outcome | Model requests | Generation seconds | Pipeline seconds |
| --- | --- | ---: | ---: | ---: |
| pubsub-rename | compilation | 3 | 109.91 | 116.97 |
| pubsub-removal | python_syntax | 3 | 106.27 | 108.81 |
| pubsub-utf8 | file_contract_or_generation_rejected | 3 | 144.49 | 145.95 |
| telemetry-rename | compilation | 3 | 122.68 | 132.02 |
| telemetry-precision | file_contract_or_generation_rejected | 3 | 136.98 | 138.69 |
| telemetry-units | independent_telemetry_semantics | 3 | 139.41 | 150.95 |

Generation includes local loading/inference wall time; pipeline includes independent analysis and validation.
Contract/generation rejections do not establish compilation or runtime behavior. Deterministic and reference replays are excluded.
This small single-trial suite is not a broad model comparison, twenty-case benchmark or human review baseline.

## Request timing

These are serving counters, not a controlled cold/warm comparison. Missing counters remain unknown.

| Migration/request | File | Contract | Load s | Prompt s | Decode s | Output tokens |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| pubsub-rename/01 | runtimes/csharp/main.cs | passed | 0.15 | 13.63 | 28.14 | 500 |
| pubsub-rename/02 | runtimes/python/main.py | passed | 0.14 | 11.24 | 20.22 | 360 |
| pubsub-rename/03 | runtimes/typescript/main.ts | passed | 0.14 | 11.78 | 23.94 | 428 |
| pubsub-removal/01 | runtimes/csharp/main.cs | passed | 0.15 | 12.16 | 24.21 | 410 |
| pubsub-removal/02 | runtimes/python/main.py | passed | 0.15 | 11.04 | 19.87 | 350 |
| pubsub-removal/03 | runtimes/typescript/main.ts | passed | 0.16 | 11.33 | 25.02 | 437 |
| pubsub-utf8/01 | runtimes/csharp/main.cs | passed | 0.17 | 14.35 | 34.94 | 578 |
| pubsub-utf8/02 | runtimes/python/main.py | passed | 0.15 | 11.58 | 27.28 | 453 |
| pubsub-utf8/03 | runtimes/typescript/main.ts | failed | 0.15 | 12.80 | 42.44 | 712 |
| telemetry-rename/01 | runtimes/csharp/Telemetry.cs | passed | 0.39 | 8.11 | 35.24 | 604 |
| telemetry-rename/02 | runtimes/python/telemetry_runtime.py | passed | 0.12 | 5.65 | 28.16 | 484 |
| telemetry-rename/03 | runtimes/typescript/telemetry.ts | passed | 0.16 | 6.08 | 38.25 | 662 |
| telemetry-precision/01 | runtimes/csharp/Telemetry.cs | passed | 0.14 | 8.13 | 37.02 | 617 |
| telemetry-precision/02 | runtimes/python/telemetry_runtime.py | passed | 0.14 | 5.69 | 37.58 | 652 |
| telemetry-precision/03 | runtimes/typescript/telemetry.ts | failed | 0.14 | 6.02 | 41.65 | 711 |
| telemetry-units/01 | runtimes/csharp/Telemetry.cs | passed | 0.16 | 8.05 | 41.53 | 704 |
| telemetry-units/02 | runtimes/python/telemetry_runtime.py | passed | 0.17 | 5.66 | 39.00 | 670 |
| telemetry-units/03 | runtimes/typescript/telemetry.ts | passed | 0.17 | 6.06 | 38.19 | 664 |

## pubsub-rename rejection evidence

- main.ts(13,108): error TS2339: Property 'name' does not exist on type 'Entity'.
- main.ts(83,45): error TS2353: Object literal may only specify known properties, and 'name' does not exist in type 'Entity'.

## pubsub-removal rejection evidence

- expected an indented block after 'if' statement on line 32 (main.py, line 33)

## pubsub-utf8 rejection evidence

- Request 03: line edit makes no change

## telemetry-rename rejection evidence

- /Users/nurlanmammadli/Documents/ChatGPT/Schema Sentinel Lab/patchgen/evidence/live-six-ministral8b-blocks001/telemetry-rename/run/proposal/workspace/runtimes/csharp/Telemetry.cs(14,52): error CS1061: 'VehicleTelemetry' does not contain a definition for 'SpeedMps' and no accessible extension method 'SpeedMps' accepting a first argument of type 'VehicleTelemetry' could be found (are you missing a using directive or an assembly reference?) [/Users/nurlanmammadli/Documents/ChatGPT/Schema Sentinel Lab/patchgen/evidence/live-six-ministral8b-blocks001/telemetry-rename/run/proposal/workspace/runtimes/csharp/CsharpApp.csproj]

## telemetry-precision rejection evidence

- Request 03: line edit makes no change
