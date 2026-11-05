# Schema Sentinel Lab evaluation

## Reproduce the deterministic benchmark

Use a full Lab clone so the pinned source revisions are available. Follow the
[demo prerequisites](demo.md) and install the
[pinned local generators](../../tools/codegen/README.md). Keep loopback ports
8000–8002 available.

```sh
python3.13 run_benchmark.py --local-codegen --output /tmp/schema-sentinel-20
```

Open the output directory's `summary.md` for per-case results and review links.
The suite compares descriptor classifications and candidate sites against
authored expectations. It regenerates bindings, builds the three runtimes,
runs tests, and checks behavior with an independent oracle. The run retains
failed cases in its denominators. Timings cover prepared local execution.
Every proposed change still requires a human decision.

The final five cases and their compatibility limits are described in
[decision 0036](../decisions/0036-twenty-migration-benchmark.md).

## Reproduce the local model evaluation

Start the local Ollama server with the same installed model and run from the
same Lab revision. The runner records its prompt version, model settings, case
coverage, actual request evidence, validation results, and elapsed time.

```sh
.venv/bin/python -m patchgen.live_suite --full-benchmark \
  --model ministral-3:8b --output /tmp/schema-sentinel-live
```

Eight cases are eligible for the live runtime-edit route. Three are schema-only
and nine require pinned policies. The report accounts for all twenty and uses
the eight eligible cases as its validation denominator. Failed attempts stay
in that denominator. A successful validation requires an actual model request,
a passing runtime gate, and a review bundle. The model workflow makes one
request per selected source file and performs zero automatic repairs.

The manual participant and review-timing exercises are deferred.
