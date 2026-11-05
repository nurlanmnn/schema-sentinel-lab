# Local model results for the twenty-case benchmark

Ministral 3 8B with candidate-edits prompt 2.5. Eight cases ran and none
produced a validated patch after 24 local requests. Three schema-only cases
and nine cases requiring pinned policies were outside the live route.

| Case | Requests | Workflow seconds | Blocking result |
| --- | ---: | ---: | --- |
| [pubsub-rename](pubsub-rename/proposal/report.json) | 3 | 168.3 | TypeScript compilation rejected malformed edits |
| [pubsub-removal](pubsub-removal/proposal/report.json) | 3 | 149.0 | Python candidate review contained an invalid or duplicate line |
| [pubsub-utf8](pubsub-utf8/proposal/report.json) | 3 | 163.0 | C# candidate decisions did not match proposed edits |
| [telemetry-rename](telemetry-rename/proposal/report.json) | 3 | 121.2 | C# and Python candidate reviews were incomplete or invalid |
| [telemetry-precision](telemetry-precision/proposal/report.json) | 3 | 129.0 | A TypeScript edit made no change |
| [telemetry-units](telemetry-units/proposal/report.json) | 3 | 140.9 | Compiled patch failed the independent telemetry check at case 1 |
| [inventory-width](inventory-width/proposal/report.json) | 3 | 138.1 | C# and TypeScript edits made no change |
| [telemetry-quantized](telemetry-quantized/proposal/report.json) | 3 | 162.4 | Python candidate review was invalid and a TypeScript edit made no change |

Model-request wall time totaled 1143.9 seconds.
Workflow times include local preparation and validation where reached.
This is one local configuration on authored cases. Human timing is deferred.

[Machine-readable report and case coverage](summary.json)
