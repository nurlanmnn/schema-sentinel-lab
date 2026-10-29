# Detector/locator adapter 1.0

`patchgen.adapter` validates supplied structured records and constructs the
existing generator contract 1.0. It does not replace the detector or locator,
infer semantic conversions from Buf prose, or certify producer completeness.

Detector record: `adapter_version: "1.0"`, nonempty `producer`, `status: "complete"`,
exact `source_revision`, the existing `change` object, and `intended_behavior`.
Supported explicit categories: field_removed, field_renamed, field_type_changed,
enum_value_added. Missing or unknown semantics must be resolved before export.

Locator record: same adapter version and revision, producer/status, `change_id`,
`old_schema_sha256`, and `files[]`. Each file supplies a runtime path, matching
language, full `source_sha256` and nonempty inclusive 1-based `positions[]` with
reason and `resolution: "resolved"`. Duplicate/overlapping spans, unsafe or
generated paths, unsupported languages, ambiguous/partial records, missing data,
wrong identity and stale HEAD/source/schema fail before prompt generation.
Source text comes from the exact Git commit and is checked against the checkout.

The producer must scan the intended scope, include constructors and reads, and
export uncertainty rather than assert complete coverage. The adapter cannot
prove that an apparently complete producer record omitted no sites. Independent
`coverage()` evaluates supplied output against reference sites separately from
prompt generation; empty truth sets have undefined recall (`null`).

Example records in `patchgen/fixtures/adapter/` are explicitly manual fixtures.
They construct the rename input exactly and have 6/6 reference-site recall by
construction. This is fixture-fed contract wiring, not live integration.

```sh
python3 -m patchgen.adapter --source EXACT_TESTBED_CHECKOUT --detector patchgen/fixtures/adapter/detector.json --locator patchgen/fixtures/adapter/locator.json --output patchgen/evidence/adapter-next
```

Outputs: `input.json` for `patchgen.generator --fixture`, plus separately retained
producer identities and record hashes. Rejected inputs retain `error.json` and
exit nonzero. The adapter sends no requests itself.

## Measured current prototype

`patchgen/evidence/locator-001/` executes the unchanged Tree-sitter function from
main `c82fee7630b982e4da2ceda9f7fb6804fb01221c` against exact testbed source
`26304c1ed2f4738676a9607e8fe21e17ebd090f0`. The independently supplied target is
Entity.name, using the existing six-site removal reference inventory.

- Python: 2/2 known sites, including the standalone assignment.
- TypeScript: 0/2; the cast-based member access and object-literal constructor are missed.
- C#: 0/2; the installed language bundle has no `tree_sitter_csharp` symbol for the prototype's language key.
- Overall: 2/6 = 33.3% line-site recall, no extra sites in these three files.
- Semgrep was not run because its executable is absent. This is not combined-locator recall.

The committed legacy v1.bin/v2.bin files refer to `model.proto`, whereas current
source uses `entity.proto`. The diagnostic parser extracts one field-removal
record from legacy descriptors. Freshly rebuilding the two source descriptors
and running the current hardwired comparison yields FILE_NO_DELETE only; its
regex extracts no field record. Different packages/paths prevent this pair from
being a clean semantic change input. Diagnostic extraction does not supply full
schemas, an exact source identity, normalized categories or intended behavior.
No separately exported detector contract was found in the inspected main tree.

The measurement exports a structured `status: partial` locator record, and the
adapter rejects it. It must not be relabeled complete or used to claim an
integrated generator. Owner follow-up: agree on a descriptor comparison identity,
export versioned structured change/impact records, resolve the C# language key,
cover cast expressions and constructor sites, and rerun independent coverage
before requesting live integration acceptance. No teammate implementation changed.

Reproduce the measurement with Python 3.11 and the already documented pins:

```sh
python -m patchgen.locator_probe --source EXACT_TESTBED_CHECKOUT --output patchgen/evidence/locator-next
```

This session used an isolated temporary Python 3.11.17 environment with
`tree-sitter==0.21.3` (MIT package metadata) and `tree-sitter-languages==1.10.2`
(Apache 2.0 package metadata). No runtime dependency manifest changed. The bundle
contains third-party grammars whose licenses need full inventory if adopted or
redistributed; this probe does not settle project-wide dependency adoption.

Acceptance for this boundary: valid manual records reproduce the exact input;
stale/missing/ambiguous records fail; reference data does not enter prompts;
coverage gaps are measured and partial real output is rejected. Technical tests
meet these bounded gates. Human interface agreement and real pipeline acceptance
remain pending.
