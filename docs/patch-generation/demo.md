# Reproduce the independent demo

Use a full clone of the personal Lab repository and check out
`codex/independent-pipeline`. Shallow clones may omit the pinned testbed ancestor.
The demo works on a trusted local checkout and never applies a patch to it.

Install Python **3.13**, Node **22+** with npm, the **.NET 8 SDK**, Git and Buf
on PATH. This launcher uses the tested Python analysis environment; the inherited
runtime-only launcher has a broader Python version range. Internet access is
required for pinned Python packages, npm/NuGet dependencies and the pinned Buf
remote generators in `buf.gen.yaml`. Ports **8000–8002** must be free. It uses
no model, Ollama service, API key or paid inference.

An existing `.venv` must also use Python 3.13. The launcher records and checks
that interpreter before installing packages; it leaves an incompatible existing
environment untouched and reports the reason.

From the clone root, run:

```sh
python3.13 run_demo.py --output patchgen/evidence/my-demo
```

On Windows, use `py -3.13` in place of `python3.13`. The default `utf8` case
supports the explicitly defined v2 identifier string-to-bytes UTF-8 policy.
Use `--case rename` for the bounded v1 name-to-display_name migration or
`--case removal` for v1 name removal with reserved number/name. Each run
needs a new output directory. The launcher creates `.venv`, installs the pinned
analysis dependencies, runs descriptor detection, syntax location, deterministic
proposal construction, compilation and independent runtime checks, then exports
a portable human-review bundle. Runtime validation installs its own dependencies
in a detached workspace. Do not run demos concurrently: the runtimes share ports.

The output contains `demo-report.json`, `demo.log`, the full `run/` evidence and
`review/index.html`. Setup failures retain a failed report and log; prerequisite
failures occur before output creation. A passing run must say
`validation_passed`. The review page still requires a real person's decision.
Use the [review instructions](review.md) to serve it locally, export a decision,
and verify the record. No automatic approval, patch application to the working
checkout, merge or deployment follows.

This is three bounded deterministic policies on one small testbed, not a live
LLM success, a twenty-case benchmark, general semantic migration or a measured
human baseline. The three historical cases above validate the relay transport. Versions and implementation revision
are retained in the demo report; pipeline snapshots retain actual source hashes.

## Include pub/sub in proposal validation

```sh
python3.13 run_demo.py --case pubsub-utf8 --output patchgen/evidence/my-pubsub-demo
```

`--case pubsub-rename` and `--case pubsub-removal` select the other two bounded
policies. These source-bound fixtures include actual subscriber modes. They run
the existing gates plus eight publications and 24 independent decoder
acknowledgements across v1/v2 topics on a local in-memory broker. The review
bundle includes the pub/sub observations and evaluator source snapshot.
These repeat the same Entity changes on a new transport baseline, not new domain
benchmark cases. See [decision 0013](../decisions/0013-pubsub-proposal-validation.md).

The active pub/sub cases also require a truncated-v1 negative control: every
subscriber must reject before acknowledgement and leave its message pending.
The review includes failure logs and cleanup evidence. This negative control is
not counted among valid deliveries or distinct schema-change cases. Earlier
retained reviews keep their older source revision and validation scope.

### Buildable telemetry rename

With the preinstalled pinned local tools described in `tools/codegen/README.md`:

```sh
python3.13 run_demo.py --case telemetry-rename --local-codegen --output patchgen/evidence/NEW-TELEMETRY-DEMO
```

This runs the independent pipeline on baseline `32e39a2`: float field 2 changes
from speed_mps to ground_speed_mps. Three real generated-binding runtimes must
preserve producer bytes, float values, observation keys and the >30 m/s predicate
for eight authored cases each. The existing Entity checks also run. Tests are
host-owned; no model requests or reference answers are used for the proposal.
The portable review retains evaluator source, all process results and the complete
validated patch. Passing only makes it eligible for human review.

`--local-codegen` is explicit and also available on the pipeline/generator CLIs.
Omitting it keeps the existing remote Buf path. The local path does not install
tools or silently retry a failed remote run. This is one distinct buildable
migration, not twenty cases, a new LLM success, or telemetry pub/sub coverage.

### Telemetry float64 precision

```sh
python3.13 run_demo.py --case telemetry-precision --local-codegen --output patchgen/evidence/NEW-PRECISION-DEMO
```

This distinct migration widens wire field 2 to double and removes the adopted C#
producer's float32 cast. Eleven cases per runtime include values float32 cannot
preserve. Producer bytes, observations and >30 m/s results must all match the
independent oracle. The wire-type change requires coordinated rollout;
mixed-version behavior is outside scope. See decision 0016.

### Explicit telemetry units

```sh
python3.13 run_demo.py --case telemetry-units --local-codegen --output patchgen/evidence/NEW-UNITS-DEMO
```

The request supplies m/s -> km/h factor 3.6, the >108.0 threshold, speed_kph keys
and an exact decoded-float JSON policy. The structural detector does not infer
unit meaning. The bounded policy changes adopted producer/predicate expressions
and observation names, then validates eight cases in each real runtime. C#
observations promote decoded float32 to double for exact numeric JSON output.
The finite cases do not prove arbitrary rounding-boundary or mixed-unit safety.
See decision 0017. All reviews remain pending a real human decision.
