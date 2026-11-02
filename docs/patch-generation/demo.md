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
LLM success, a twenty-case benchmark, general semantic migration, pub/sub
integration or a measured human baseline. Versions and implementation revision
are retained in the demo report; pipeline snapshots retain actual source hashes.
