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
.venv/bin/python -m patchgen.pipeline --output patchgen/evidence/my-pipeline
```

The command above reliably stops after production records and adapter input.
To exercise the full validation path with a known-correct proposal:

```sh
.venv/bin/python -m patchgen.pipeline --output patchgen/evidence/my-reference --response patchgen/reference/entity-name-rename/response.json
```

This is an offline evaluator replay, not a live model success. Experimental live
generation adds `--generate --strategy syntax_rename` for prompt 2.6 token editing,
or `--generate` alone for prompt 2.5 general line edits. Neither new live strategy
has a passing result; see the retained failures before interpreting the output.

The default case is the pinned v1 name-to-display_name migration. Start
`ollama serve` first if it is stopped. The output directory must be new. Omit
`--generate` to stop after detector, locator, measurements and adapter. The optional token strategy uses prompt 2.6: model-selected AST token replacements
with host-preserved layout. Omit `--strategy syntax_rename` to use the general
line-edit prompt 2.5. Token editing rejects non-rename cases. For the
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
Generation adds raw model responses, per-candidate decisions,
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
this analysis. Known unsupported runtime source extensions make the record partial; other unknown extensions are not parsed. Generated code,
tests, libraries and code outside runtimes are excluded. Enum change detection
works structurally, but enum consumer location is explicitly unsupported and
adapter rejection is expected. Imported/multi-file schema resolution is outside
this single-file build and fails when dependencies are unavailable.

See decisions 0004/0005 for candidate review, token-edit boundaries and dependency
license records. Generated naming is bounded to the tested snake/camel/Pascal
conventions; acronym/reserved-word edge cases need separate validation.
Current live outcomes are recorded separately in `independent-results.md`.

## Role-constrained rename follow-up

Prompt 2.7 is selected explicitly:

```sh
.venv/bin/python -m patchgen.pipeline --output patchgen/evidence/my-role-rename --generate --strategy syntax_rename_roles
```

The host gives recognized TypeScript syntax roles one allowed replacement and
requires all inventory tokens on each edited candidate line. Unsupported roles
fail closed. Candidate selection is still a model decision, receiver identity is
unproved, and mixed affected/unaffected tokens on one line are unsupported.
The observation policy is the narrow explicit convention described in decision
0006. This is a hybrid proposal strategy, not unconstrained code generation.

To produce the bounded rename proposal without a model, explicitly use
`--generate --strategy deterministic_rename_roles` in a fresh output directory.
This proposes every located token using descriptor/role-derived names, records
that receiver identity is unproved, and runs the same independent validation.
It reads no reference response and makes zero model requests. Human review is
required; this cannot be counted as a live model result or a type migration.

## Bounded UTF-8 type migration

```sh
.venv/bin/python -m patchgen.pipeline --fixture patchgen/fixtures/v2-identifier-bytes/runtime-input.json --output patchgen/evidence/my-utf8-proposal --generate --strategy deterministic_utf8_v2
```

This explicit policy supports the adopted testbed's v2 singular entity_id
string-to-bytes change with valid UTF-8 textual observations. It uses no model or
reference response. Constructor/observation syntax and version dispatch must
match supported shapes; unmatched candidate lines reject. v1 candidates remain
unchanged. This is not arbitrary type/semantic migration. See decision 0007.

Add `--review-output NEW-SIBLING-DIRECTORY` to a proposal run to export a local
human-review page after validation/rejection. See [review workflow](review.md).
The review copies evidence, hashes artifacts and exports human decision records;
it never applies or merges code. No real human approval is implied by export.
