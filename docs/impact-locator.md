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
A separate bounded TypeScript layer now follows exact generated imports and
immutable const decoder/encoder flow. C# matches and unknown receivers stay
candidate-only.
The [binding decision](decisions/0025-bounded-python-binding-evidence.md) defines
assumptions, supported syntax and downstream enforcement limits. The authored
69-case component suite runs with `python -m patchgen.analysis_corpus`; use the
prepared `.venv` and a fresh `--output` directory.

The current adapter verifies the supported tracked-runtime scan manifest and
recomputes positive Python/TypeScript evidence from the pinned source before preserving it.
It rejects missing bound lines/files and altered or stripped evidence. Legacy
supplied records without the manifest have narrower provenance. Computed Python
reflection is a review candidate with unknown field identity, never a bound claim.
Subscripts with an identifier key now also match same-file initializers containing
a decoded field-name literal. The initializer and index use become separate syntax
candidates. Scope, rebinding and control flow are not resolved; shadowed names can
add candidates. Unknown keys keep the bounded `entity`/`decoded` receiver heuristic.
An arbitrary `vehicle[key]` with no local field-name initializer can still be missed.

New scan manifests (version 1.1) include every tracked runtime-tree entry with its
Git mode and object ID. Unknown files, unsupported paths, symlinks and submodules
block completeness. A narrow auxiliary build/dependency-file policy is explicit
in [decision 0026](decisions/0026-explicit-runtime-tree-inventory.md). The adapter
recomputes this inventory instead of trusting a producer's completion status.

Name matching now decodes escaped TypeScript/C# identifiers, ordinary quoted
string keys, static TypeScript templates and C# verbatim strings. Python names
use NFKC normalization; string values do not. C# identifier formatting characters
are ignored following compiler behavior. C# raw literals and interpolated keys
remain outside this bounded literal decoder. C# reflection member names are
read from syntax nodes, including escaped spellings, rather than a regex over
invocation text. These improvements add lexical recall, not receiver proof.

[Decision 0027](decisions/0027-bounded-typescript-binding-evidence.md) defines the
TypeScript boundary. It does not use casts/annotations as identity or propagate
outer local values into closures. Positive claims require the declared standard
ts-proto codec API and no arbitrary monkeypatching. The real telemetry source has
required rename references at TS lines 9–11 alongside Python lines 10–12; C# has
no binding claims. The adapter checks both supported binding layers from source.

Current locator producers must supply their advertised manifest capabilities.
Version 1.4 onward requires manifest 1.1; version 1.3 requires a manifest. Orphaned
scan/inventory fields cannot silently enter the legacy path. This checks record
consistency, not producer authentication; genuinely supplied legacy records retain
their narrower provenance.

Required-reference flags are language-specific: a rename that preserves the
generated TS member (for example `speed_mps -> speedMps`) retains binding evidence
without forcing an edit. Removals and known distinct generated-member renames
remain required. Unsupported new member spellings record an unresolved limitation.

The adapter also rebuilds old/new descriptors for advertised detector version
1.1 onward. It requires the same supported event, classification and hashes
before using binding evidence. Genuine legacy detector fixtures keep supplied
classification with narrower provenance. This reuses the owning detector and
checks consistency; it neither authenticates producers nor proves semantics.

TypeScript binding evidence accepts static string or no-substitution template
keys for field reads, declared namespace/codec access and computed encoder object
keys. Exact original literal token ranges are recorded. Interpolated or variable
keys do not establish a codec or a bound field.

The detector compares compiler-generated proto3 optional presence groups by field
number when their own field is renamed. Events preserve the actual old and new
group names. An unrelated group-name change requires review. Real
oneof changes still block adaptation. The locator considers descriptor JSON keys
and old presence-group string names. Its C# candidates include pinned protoc
property names, field-number constants and explicit proto3 optional Has/Clear
members. These names do not resolve C# receivers or reflection calls.

Python records exact single-string tokens passed to unshadowed `getattr` or
`hasattr` and standard Protobuf `HasField` or `ClearField` on a bound instance.
Shadowed builtin names, unknown receivers and compound strings stay candidates.
Branch-defined classes/functions and repeated imports invalidate inherited
module identities.

For locator 1.10 and later, the adapter reruns the syntax scan over every pinned
source in the verified manifest. Omitted or fabricated candidates and a forged
complete status on a scan with warnings are rejected. This uses the owning
scanner and checks consistency under the current implementation. Regenerate
records when scanner behavior changes.

Python reflection scanning also follows direct builtin imports and same-file
callable aliases. Dynamic or starred keys require review. When a reflected
identifier has a matching literal initializer, both the call and the
initializer are candidates. The alias scan combines file-wide possibilities,
so rebinding can create extra warnings.
