# Testbed development

Start with the [local setup instructions](../README.md). All commands below run
from the repository root.

## Start all services

Windows:

```powershell
py run_local.py start
```

macOS and Linux:

```sh
python3 run_local.py start
```

This builds the code and keeps all three services running. Dependencies must
already be installed by the first run. Press Ctrl+C to stop the services.

| Service | Health check |
| --- | --- |
| Python | http://127.0.0.1:8000/health |
| TypeScript | http://127.0.0.1:8001/health |
| C# | http://127.0.0.1:8002/health |

Open a health-check URL in your browser to confirm that a service is running.
Logs are saved in `testbed/artifacts/python.log`, `typescript.log`, and `csharp.log`.

To send the four test messages while the services are running, open a second terminal:

```powershell
# Windows
.venv\Scripts\python.exe testbed/tests/e2e_test.py
```

```sh
# macOS and Linux
.venv/bin/python testbed/tests/e2e_test.py
```

Each test checks the fields decoded by Python, TypeScript, and C#, the returned
message, and the service order. The cases use normal strings, empty strings,
Unicode, and escaped text.

## Run individual examples

These print one decoded entity and exit. They do not start servers.

```powershell
# Windows
.venv\Scripts\python.exe runtimes/python/main.py
```

```sh
# macOS and Linux
.venv/bin/python runtimes/python/main.py
```

These commands work on all three operating systems after setup and a build:

```sh
npm start --prefix runtimes/typescript
dotnet run --project runtimes/csharp/CsharpApp.csproj
```

Add `--version v2` to the Python command, `-- --v2` to the npm command, or
`-- --v2` to the dotnet command to use the existing name-removal example.
The HTTP test uses v1.

## Docker (optional)

With Docker Compose installed, run:

```sh
docker compose -f testbed/compose.yaml --profile test up --build --abort-on-container-exit --exit-code-from roundtrip-test
docker compose -f testbed/compose.yaml --profile test down --remove-orphans
```

The second command removes the test containers. On macOS and Linux,
`make test-docker` runs both steps automatically.

## Local pub/sub fan-out (independent Lab)

After `python3 run_local.py setup`, run:

```sh
python3 run_local.py pubsub --output patchgen/evidence/my-new-pubsub-run
```

Use a new output directory each time. This builds TypeScript/C#, runs testbed
unit checks, starts an in-memory broker on a random loopback port, starts three
subscriber processes, and publishes eight independent wire-encoded protobuf
inputs to the two topics in `pubsub/topics.json`. It checks every runtime's
acknowledgement fields, delivery order and recipient inventory, and then stops
all children and the broker. It uses no model or external broker dependency.

`report.json`, `expected.json`, `broker-state.json` and each runtime's log retain
hashes, observations, timing scope and cleanup outcomes. An already built checkout
can run `.venv/bin/python -m testbed.pubsub.run --output NEW-DIRECTORY` directly.

This is separate from the HTTP relay and the older pinned patch-validation
fixtures. The broker is local, bounded and volatile; no durable delivery,
exactly-once processing, authentication or network-failure recovery is claimed.
See [decision 0012](../docs/decisions/0012-local-pubsub.md) for the HTTP contract.
The samples are not additional schema-change cases or a human baseline.

To exercise the truncated-payload failure boundary against built runtimes:

```sh
.venv/bin/python -m testbed.pubsub.run --scenario malformed --output patchgen/evidence/my-new-negative-control
node testbed/pubsub/check-decoder.cjs
```

The first command requires all three processes to exit with protobuf decoder
errors, no acknowledgement and one retained pending message per subscriber.
Its success status is `expected_rejection_observed`, not `passed` delivery.
The second checks Buffer/plain-array handling in the TypeScript processor for
both versions. This covers truncated length-delimited fields only, not all
malformed protobuf or fault recovery. See decision 0014.

## Telemetry producer/consumer checks

The canonical `proto/telemetry/vehicle.proto` is generated into each language.
The runtime `--telemetry` mode reads a small JSON request array on stdin, decodes
its Protobuf payloads and constructs independent samples using generated bindings.
It is a local benchmark interface, not another HTTP service or pub/sub topic.
After the normal build, run:

```sh
.venv/bin/python -m testbed.telemetry.run --case baseline --output patchgen/evidence/NEW-TELEMETRY-BASELINE
```

Eight cases per runtime check exact wire construction, float values, canonical
observation keys and strict >30 m/s behavior. The evaluator imports no generated
bindings. `run_demo.py --case telemetry-rename` validates a proposed rename
against a host-owned copy of that evaluator and exports review evidence.
