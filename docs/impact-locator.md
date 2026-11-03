# Deterministic schema and impact analysis

The active implementation is `patchgen.detector` plus `patchgen.locator`, invoked
through `patchgen.pipeline`. The descriptor detector compares old/new schemas
with matching file and package identity. The locator parses tracked runtime
sources in Python, TypeScript and C# with the pinned Tree-sitter grammars.

From the prepared analysis environment, run a new output directory:

```sh
.venv/bin/python -m patchgen.pipeline --fixture patchgen/fixtures/telemetry-speed-rename/runtime-input.json --output patchgen/evidence/NEW-analysis
```

This command does not generate patches or call a model. See the
[pipeline guide](patch-generation/independent-pipeline.md) for environment setup.

Outputs include descriptors' hashes, classified structural changes, scanned
source identities, candidate positions, issues, adapter provenance and measured
coverage when an independent inventory exists. Ground truth is consulted for
measurement after production analysis, not supplied to the locator.

The current locator finds conservative syntax candidates, not proven receiver
types or whole-program dependencies. Its `complete` status means the declared
scan completed, not that every candidate is semantically affected. Alias/dataflow,
arbitrary reflection, unsupported languages and enum consumers require more work.
Unit changes and other semantic meanings require an explicit policy.

The November 3 priority is to strengthen these deterministic boundaries and
broaden independent evaluation before more patch-generation or fine-tuning work.
See [decision 0024](decisions/0024-deterministic-analysis-priority.md).

The original `impact_locator.py`, committed `v1.bin`/`v2.bin`, and
`patchgen.locator_probe` were retired from the active checkout. They depended on
diagnostic prose, stale descriptor identities and an incompatible older grammar
bundle. Their source remains in Git history, and historical measurements and
raw evidence remain retained. They are not alternate supported entry points.

As of the [November 3 hardening checkpoint](deterministic-analysis-2026-11-03.md),
positions explicitly say `candidate`. A bounded Python layer separately records
canonical import/constructor/parser evidence and required rename/removal references.
It does not promote TypeScript/C# matches or unknown receivers to type proof.
The [binding decision](decisions/0025-bounded-python-binding-evidence.md) defines
assumptions, supported syntax and downstream enforcement limits. The authored
26-case component suite runs with `python -m patchgen.analysis_corpus`; use the
prepared `.venv` and a fresh `--output` directory.
