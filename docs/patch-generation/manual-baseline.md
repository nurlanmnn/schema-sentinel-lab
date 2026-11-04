# Manual telemetry baseline

Use this workflow for the m/s to km/h telemetry migration. The participant
receives the pinned schema, generated bindings, runtime sources and task
brief. The evaluator keeps the reference patch, locator output and checks.

## Prepare a participant kit

From a full Lab clone with Python 3.13:

```sh
.venv/bin/python run_manual_baseline.py prepare --output /tmp/telemetry-kit
```

Give the participant that directory. Ask them to follow `SETUP.md` before
opening `TASK.md` and to return their first patch and active elapsed seconds.
Use the manifest hashes to verify the distributed kit. Record any prior
exposure to the solution or deviation from the protocol before comparing
timings. Keep each first attempt, including failures.

## Evaluate a submission

Install the [pinned local codegen tools](../../tools/codegen/README.md) and
use the [demo prerequisites](demo.md). Run evaluations sequentially because
the testbed uses loopback ports 8000–8002. This executes the submitted runtime
code, so use this local evaluator with trusted participants' submissions.

```sh
.venv/bin/python run_manual_baseline.py evaluate \
  --kind human_submission --elapsed-seconds "$REPORTED_SECONDS" \
  --patch /path/to/submission.patch --output /tmp/telemetry-attempt-01
```

The evaluator starts from the pinned revision and verifies the patch scope
and exact target schema. It regenerates bindings and runs the same build,
unit tests, round trip and independent 24-case runtime check as the automated
telemetry case. The report keeps the submitted patch hash, source revision,
self-reported active time and evaluator elapsed time separate. Passing checks
leave human approval pending. Review time requires a separate timed review.

## Synthetic check

The evaluator accepts `--kind synthetic_dry_run` for a known patch or negative
control. Omit `--elapsed-seconds` in this mode. The retained synthetic check
shows evaluator behavior only. Human timing and approval remain unmeasured
until a real participant and reviewer complete those steps.
