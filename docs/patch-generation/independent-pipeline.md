# Independent detector/locator pipeline

This Lab implementation builds old/new Protobuf descriptors with matching file
and package identity, locates conservative runtime syntax candidates in Python,
TypeScript and C#, and feeds normalized records into adapter 1.0 and the existing
isolated patch generator. Human approval is always required.

Use Python 3.13 and the existing Buf, Node 22+, .NET 8 and local Ollama setup.
No additional model is needed if `ministral-3:8b` is already installed.

```sh
python3 -m venv .venv
.venv/bin/pip install -r patchgen/pipeline-requirements.txt
.venv/bin/python -m unittest discover -s patchgen/tests -v
.venv/bin/python -m patchgen.pipeline --output patchgen/evidence/my-pipeline --generate
```

The default case is the pinned v1 name-to-display_name migration. Start
`ollama serve` first if it is stopped. The output directory must be new. Omit
`--generate` to stop after detector, locator, measurements and adapter. For the
UTF-8 type migration, pass
`--fixture patchgen/fixtures/v2-identifier-bytes/runtime-input.json`.
For removal use `patchgen/fixtures/entity-name-removal/runtime-input.json`.
The request must supply exact `source_revision`, `change` (id, schema_path,
old_schema, new_schema), and intended_behavior. Supplied category and old
manual affected_files are ignored: production classification and positions are
computed independently. Old schema is checked against the commit. Both schemas
are built independently at that same path; this never compares different v1/v2
packages as if they were two versions of one identity.

Retained outputs include detector/locator records, schema and descriptor hashes,
all scanned source hashes, candidate reasons, independently computed coverage,
adapter input/provenance, implementation snapshots, and isolated source checkout.
Generation adds prompt 2.5, raw model responses, per-candidate decisions,
proposal/validation reports and complete review patches. Trusted test migrations
remain evaluator-owned and excluded from model prompts. The pipeline never reads
reference answers until after its production scan, solely for measurement.

`--response PATH` explicitly replays a reference proposal for offline harness
validation. It is never counted as a live model success. New live attempts use
new output directories; earlier failures are kept.

## Measured scope

The pinned removal, rename and UTF-8 type cases each have six independently
specified runtime line sites across three languages. All 18 are recovered.
Removal and rename have no extra sites against these inventories. The type case
returns three extra candidates in unchanged v1 branches (C# lines 15/38 and
TypeScript line 59). The model must explain why these remain unaffected.
These are three related cases in one intentionally small testbed, not a broad
recall estimate. Structural/negative tests are not additional realistic benchmark
cases and there is no measured human baseline or calibrated confidence.

Complete means the declared tracked runtime source scan finished without known
parse/dynamic errors. Receiver types, imports, aliases, data flow, templates,
macros and whole-program semantics are not resolved. Identifier matching can
produce false positives. Selected literal reflection is located; known dynamic
reflection/access is flagged. Arbitrary indirect/reflection patterns can escape
this analysis. Unknown runtime file extensions are not parsed. Generated code,
tests, libraries and code outside runtimes are excluded. Enum change detection
works structurally, but enum consumer location is explicitly unsupported and
adapter rejection is expected. Imported/multi-file schema resolution is outside
this single-file build and fails when dependencies are unavailable.

See decision 0004 for candidate-review rules and dependency license records.
Current live outcomes are recorded separately in `independent-results.md`.
