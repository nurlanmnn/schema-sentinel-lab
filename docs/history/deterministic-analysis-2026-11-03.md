# Deterministic analysis checkpoint — November 3, 2026

This checkpoint strengthens the descriptor/locator boundary before further patch
generation. No model requests, generated proposals or human approvals were made.
The team checkout and disabled upstream push URL remain outside the work.

## Detector correctness

The detector now handles package-less qualified names consistently, retains the
old/new field identity (including named message/enum types), and reports explicit
structural outcomes even when no generation-compatible event exists. It blocks
enum reordering/default changes and changes to the first alias of an existing
number. It permits additions that preserve those existing meanings, without
claiming enum consumer completeness. Companion services, metadata, presence,
reservations and declaration changes cannot silently ride along with a rename.
The supported single-event boundary remains intentionally narrow.

## Source evidence

Positions are candidates. Python imports, constructors/parser calls and aliases
can add bounded canonical binding evidence under a declared generated-module
policy. TypeScript/C# matches, dynamic version imports and unresolved Python
receivers remain candidates. The evidence and limitations are carried separately;
see [decision 0025](../decisions/0025-bounded-python-binding-evidence.md).

The original telemetry rename's Python lines 10, 11 and 12 all receive positive
binding evidence. Line 12 is the strict `entity.speed_mps > 30.0` threshold that a
previous model incorrectly dismissed. The candidate-review boundary now rejects
that dismissal. This is a static regression, not a new model trial or migration.

## Authored component evaluation

Run from the prepared environment into a new evidence directory:

```sh
.venv/bin/python -m patchgen.analysis_corpus --output patchgen/evidence/NEW-binding-corpus
```

The 26 authored source examples cover import/class/instance aliases, parser and
constructor access, thresholds, local imports, unchanged versions, unrelated
objects, scope shadowing, rebinding, branches, closures, comprehensions, lambdas,
annotations, reflection and TypeScript/C# candidates. Inventories are authored
source inspection, not a measured independent human baseline. Expected outcomes
are consulted after production results, and a scorer regression checks that
changing expectations does not change the analysis.

`patchgen/evidence/binding-corpus-checkpoint001/summary.json` records:

| Measurement | Result |
| --- | --- |
| Component cases matching declared expectations | 26/26 |
| Known affected candidate lines recovered | 18/19 |
| Extra candidate lines | 8 |
| Expected bounded-reference lines recovered | 8/8 |
| Extra binding claims | 0 |
| Model requests / validated migrations | 0 / 0 |

A computed `getattr(entity, field_name)` is warned about but lacks a concrete
candidate line in this first checkpoint. That is a real recall limitation even
though the expected unsupported behavior matches its inventory. The report retains
the miss. These small authored cases establish regression behavior, not broad
recall, precision, runtime import validity or end-to-end migration success.

## Validation

All 178 patchgen tests pass in
`patchgen/evidence/deterministic-hardening-unit001/tests-final.log`. The first full run
failed because five retained deterministic policies matched entire event dicts;
those callers now check their explicit supported event constraints while allowing
additive detector evidence. The failure log is retained beside the passing run.
No active strategy was retired merely because it was experimental.

The retained eight-case domain corpus also matches 8/8 expectations (45/45 known
lines, two enum-import extras). The analysis-only telemetry smoke recovers 9/9
known runtime lines with no extras and records the three Python required lines;
see `binding-domain-corpus001` and `binding-telemetry-smoke002`. All 27 testbed
unit tests pass in the same unit evidence directory.

## Follow-up: reflection candidates and verified source inventories

The active source suite now has 32 authored examples. The original 26 cases
recover 19/19 affected lines after computed reflection becomes a warning plus a
candidate. Six additional literal/reflection/subscript cases expose a remaining
scope limit: `vehicle[key]` with an arbitrary receiver spelling is not covered by
the retained `entity`/`decoded` subscript heuristic. It remains a measured miss;
expanding all subscripts indiscriminately also pulled HTTP-header operations into
blocking impact reports, without establishing schema identity.

`reflection-binding-corpus001/summary.json` records 32/32 declared expectation
matches, 24/25 affected candidate lines, eight extra candidates, and 8/8 expected
bound lines with no extra binding claims. Matching an expected limitation does
not repair that limitation. Dynamic access remains uncertain and review-blocked;
escaped and concatenated Python string keys now compare their actual values.
Non-Python literal decoding remains limited to plain quoted strings.

The locator now declares a supported-source scan manifest. The adapter checks its
paths/languages/hashes against the exact tracked runtime tree and recomputes
positive Python evidence under the declared policy. It rejects dropped required
lines, omitted Python files containing bound references, altered evidence, missing
flags, incomplete manifests and stale hashes. Legacy supplied fixture records
without that manifest remain readable with explicitly narrower provenance.
Recomputing uses the same bounded algorithm; this is consistency enforcement, not
an independent proof of whole-program completeness. Unknown source extensions,
external code, dynamic imports and arbitrary aliasing remain limitations.

All 183 patchgen tests pass in
`deterministic-boundary-unit002/tests-final.log`. The analysis-only
`binding-boundary-smoke001` still recovers 9/9 telemetry lines with no extras and
retains three required Python lines. No model or migration validation was run.

## Follow-up: Python scope audit

Adversarial source inspection found stale positive bindings after `match`
captures and definition-header assignment expressions, plus namespace mutation
hidden in class bodies or accessed through qualified builtins/`vars`. Added
three regression groups with fourteen negative source examples, retained the
failing run, and widened conservative invalidation. Removed the superseded
statement-only namespace-mutation collector rather than keeping two competing
checks. Unsupported sites remain syntax candidates.

`patchgen/evidence/python-scope-audit001/` retains before/after unit logs, a
source snapshot and regression tests. All 186 patchgen tests pass. The existing
32-case component corpus still matches 32/32 authored expectations, with 24/25
affected candidate lines, eight extras, 8/8 expected bound lines and zero extra
binding claims (`python-scope-corpus001`). These measurements remain static
component evidence, not validated migrations or a human baseline. No model
requests or patch proposals were made.

## Follow-up: Runtime-tree inventory

Replaced the source-extension allowlist's silent skips with a complete Git tree
inventory and an explicit auxiliary build-file policy. Unknown extensions,
extensionless files, unsupported paths, symlinks and gitlinks block completion.
New manifest 1.1 rows are checked again by the adapter against the pinned tree.
Language policy is shared rather than duplicated in locator and adapter.

All 192 patchgen tests pass, including six real-Git-tree regression groups covering
Unicode filenames, executable modes, symlinks, submodules, unsafe filenames,
unknown extensions and forged inventory. Evidence is in
`patchgen/evidence/runtime-inventory-audit001/`. The eight-domain-case corpus
still matches 8/8 authored outcomes (`runtime-inventory-domain001`), and the
analysis-only telemetry smoke adapts with 9/9 known lines and zero extras
(`runtime-inventory-smoke001`). Source snapshots are retained; temporary source
checkouts were removed. No proposals, model requests or human acceptance occurred.

## Follow-up: Python identifier spelling and token ranges

An authored fullwidth field identifier reproduced a candidate miss and incorrect
binding byte columns. Python normalizes identifiers in its AST but keeps original
source offsets. The locator now normalizes identifier comparisons, and the binding
layer indexes exact source NAME tokens rather than subtracting the normalized
field-name length. Two regression groups cover normalized constructor keywords,
attribute accesses, non-ASCII prefixes and multiline tokens. Evidence retains the
failing reproduction and source snapshots in `python-token-audit001`.

All 194 patchgen tests pass. The unchanged 32-case component corpus retains its
24/25 affected candidate lines, eight extras and 8/8 expected bound lines with no
extra claims (`python-token-corpus001`). This adds a bounded lexical capability;
it does not change the documented arbitrary-receiver/dataflow limitations. No
model requests or migration proposals occurred.

## Follow-up: Cross-language source spellings

Added bounded language-specific decoding for TypeScript/C# escaped identifiers
and string keys, static TypeScript templates and C# verbatim strings. Identifier
normalization stays language-specific: Python uses NFKC, C# ignores formatting
characters, and JavaScript does neither. String values are never normalized as
identifiers. C# reflection calls use parsed member names, replacing the previous
invocation-text regex. Normalized Python reflection/receiver spellings also remain
review candidates. No receiver/type claims were added for TypeScript or C#.

Eight authored source-spelling cases expand the component corpus to 40. Current
results are 40/40 expected outcomes, 42/43 affected candidate lines, eight extras,
10/10 expected bound lines and zero extra binding claims. The remaining miss is
still the arbitrary dynamic-subscript receiver. All 202 patchgen tests pass.
`source-spelling-audit001` retains failing/final tests, implementation snapshots,
and runnable Node/.NET lexical sanity fixtures. Node and .NET outputs confirm the
language distinctions; the .NET fixture restored only from an empty local source,
with no new external package. These fixtures do not validate generated bindings
or migrations. `source-spelling-corpus001` retains the expanded corpus results.
No model requests, proposals or human acceptance occurred.

## Follow-up: TypeScript const/source-binding evidence

Added a bounded ts-proto layer for exact generated-module imports, immutable const
aliases, direct decode results, encoder object keys and field reads. Parameter,
loop, class and enclosing-scope shadowing, visible namespace mutations and
unsupported TypeScript namespaces suppress claims. Mutable variables, casts,
annotations and outer local captures remain candidates. Audits reproduced and
retained scope/mutator counterexamples before fixing them. Shared dispatch lets
the adapter recompute TS claims and reject altered evidence or dropped references.

All 213 patchgen tests and 27 testbed tests pass. Fourteen authored TS boundary
cases expand the component corpus to 54: 54/54 expected outcomes, 48/49 affected
candidate lines, 18 extras, 15/15 expected binding lines and zero extra claims
(`typescript-binding-corpus002`). The previous 52-case run remains retained.
These are source inventories, not migration successes or a human baseline.

The real analysis-only telemetry smoke still adapts with 9/9 known lines and no
extras; Python lines 10–12 and TypeScript lines 9–11 carry required rename
references. C# remains unbound. The eight-domain-case corpus still matches 8/8.
Evidence is in `typescript-binding-audit001`, `typescript-binding-smoke001` and
`typescript-binding-domain001`. The audit's final implementation snapshots include
the final adapter guards; earlier smoke/corpus snapshots preserve their exact
pre-commit implementations. Temporary source checkouts were removed. No model
requests, generated migration proposals or human approvals occurred.

## Follow-up: Dynamic builtin references and manifest downgrade

Authored regressions reproduced positive Python binding claims after aliased
mutation builtins and annotation assignment expressions. References to mutation/
introspection builtins now disable evidence before values can escape through
aliases or defaults. Assignment expressions anywhere disable evidence; this
replaces the narrower definition-header check. Syntax candidates remain available.
The rejection pass can suppress harmless shadowed names and is not a whole-program
side-effect analysis. Failing/final focused logs and a source snapshot are in
`python-dynamic-reference-audit001`.

The adapter also rejected neither a stripped current manifest nor an advertised
1.1 inventory downgraded to 1.0. Current producer capabilities now require their
manifest version; orphaned scan fields are rejected. Genuine legacy fixtures are
still accepted with narrower provenance. Producer strings are not authenticated.
Before/after tests and a source snapshot are in `manifest-contract-audit001`.

All 217 patchgen tests pass. Two authored Python cases bring the component corpus
to 56/56 expected outcomes, 48/49 affected candidate lines, 20 extras, 15/15 expected
bound lines and zero extra claims (`python-dynamic-reference-corpus001`). The
full-suite initial failure was a stale aggregate extra-count assertion after
adding two deliberately unbound cases; the retained log records it. No model
requests, migration proposals or human approvals occurred.

## Follow-up: Generated member identity versus schema rename

An authored regression reproduced a required TS edit for the schema rename
`speed_mps -> speedMps`, although local protoc 25.1/ts-proto 1.165.0 generate the
same `speedMps` member for both versions. Binding identity remains attached, but
a shared locator/adapter rule requires an edit only for removal or a known
generated-member change. Python's field still changes. Unsupported new TS member
spellings record an unresolved edit-requirement limitation. No type annotations
or casts establish identity. The bounded naming subset now includes lower-initial
mixed case, matching the inspected pinned generator's default key conversion.

All 219 patchgen tests pass. Evidence in `runtime-member-rename-audit001` includes
the failing regression, final tests, a real Git-tree adapter test, implementation
snapshots and both generated TS files. An intermediate focused failure was a
wrong test review-line number; its log is retained. No models, generated migration
proposals or human acceptance were involved.

## Follow-up: Class/codec aliases through containers and conditionals

Independent adversarial examples reproduced retained binding claims after visible
mutations through arrays/lists, dictionaries/objects, conditional expressions,
boolean expressions, bracketed namespace aliases and stored object properties.
The rejection-only alias pass now propagates those possible class/codec values;
no positive receiver identity is inferred through them. Call results remain
excluded, preserving ordinary message-instance field writes. Unknown call effects
and arbitrary monkeypatching are still outside the declared source policy.

All 221 patchgen tests pass, including explicit positive instance-write checks.
Three authored corpus cases bring the suite to 59/59 expected outcomes, 48/49
affected candidate lines, 23 extras, 15/15 expected bound lines and zero extra
claims. Evidence and before/after logs are in `container-binding-audit001` and
`container-binding-corpus001`. No model requests, migration proposals or human
approvals occurred.

## Follow-up: Recheck advertised detector event identities at the adapter

A live detector record could drop its event or supply a different message/field
identity and enter adaptation with stripped required-reference evidence. The
adapter now rebuilds descriptors for advertised detector 1.1 onward and verifies
the single supported classification, event, schema hashes and descriptor hashes.
Forged unsupported/structural outcomes also reject. Legacy supplied detector
fixtures remain readable with explicit narrower provenance. This is consistency
validation using the owning detector, not independent verification or producer
authentication.

All 222 patchgen tests and 27 testbed tests pass. The analysis-only telemetry
smoke adapted with 9/9 authored lines and zero extras. Evidence is in
`detector-contract-audit001` and `detector-contract-smoke001`; the temporary source
checkout was removed. No model requests, proposals or human approvals occurred.

## Follow-up: Named literal field keys across runtime languages

Python, TypeScript and C# now report a field-name literal initializer and a
same-file index using its variable name as separate candidates. This recovers
source edit/context lines behind `vehicle[key]` when there is a visible matching
initializer. The name match does not model shadowing or rebinding; a fourth authored
case measures the two resulting extras. Unrelated header keys, unused literals
and unknown arbitrary index expressions do not become blanket warnings. The
original caller-supplied arbitrary-key miss remains visible.

All 224 patchgen tests pass. The 63-case component corpus matches 63/63 expected
outcomes, 54/55 affected candidate lines, 25 extras and 15/15 bound lines with zero
extra binding claims. All eight domain expectations still match. Evidence is in
`named-field-key-audit001`, `named-field-key-corpus001` and `named-field-key-domain001`.
Temporary domain source checkouts were removed. No migration proposals or model
requests occurred.

## Follow-up: Static computed TypeScript keys

Static quoted/template bracket keys now preserve declared TS module/codec identity
through direct encode/decode calls, decoded field reads and computed encoder keys.
Interpolated and variable keys cannot establish those identities. The syntax scan
now finds computed literal object keys, and binding evidence keeps original byte
ranges. Two authored cases add five bound affected lines, with a deliberately
unbound dynamic method result.

All 226 patchgen tests pass. The final 65-case authored component corpus matches
65/65 expected outcomes, 59/60 affected candidate lines, 26 extras, 20/20 bound
lines and zero extra binding claims. The telemetry smoke adapted with 9/9 authored
lines and zero extras. Logs and source snapshots are in `ts-static-computed-key-audit001`,
`ts-static-computed-key-corpus002` and `ts-static-computed-key-smoke001`; the earlier
64-case run is retained. The temporary smoke checkout was removed. No models or
migration proposals ran.

## Follow-up: Proto3 optional presence and generated member names

A proto3 optional field rename now compares its synthetic oneof by owning field
number. The event retains actual group names, including compiler collision
prefixes. Real oneof changes remain unsupported. The locator can find the old
presence group in string references and use the descriptor's JSON spelling for
literal or named-key candidates. C# gains generated property names, reserved API
suffixes, field-number constants and explicit proto3 optional Has/Clear names.
These are syntax candidates.

All 230 patchgen tests passed. The normal detector/locator path is exercised on an
authored pinned Git tree, and local protoc 25.1 confirms the generated names in
`optional-presence-audit001`.

## Follow-up: Python reflection and conditional definitions

Branch-defined classes/functions and repeated imports now withdraw inherited
Python module claims. An imported generated class can be replaced by a conditional
definition or a different import at a call site. The straight-line binding policy
also recognizes exact single-string keys in unshadowed builtin reflection and
standard Protobuf HasField/ClearField calls on a known instance. Compound keys
and shadowed or unrelated receivers stay unbound.

All 232 patchgen tests passed. The 67-case component corpus matched 67/67
expectations, 61/62 affected lines and 24/24 expected binding claims with no extra
binding claims. There were 27 extra syntax candidates. Evidence is in
`python-reflection-audit001` and `python-reflection-corpus001`.

## Follow-up: Verify candidate-only lines at the adapter boundary

The adapter now reruns current locator syntax scans across the pinned runtime
inventory. It rejects a dropped C# candidate line or file, a fabricated candidate
or reason, and a complete status that hides dynamic warnings. The candidate
verification is recorded separately from binding and detector verification.
Earlier locator records retain narrower provenance.

All 234 patchgen tests and 27 testbed tests passed. The telemetry analysis
adapted with 9/9 affected lines and zero extras. Evidence is in
`candidate-contract-audit001` and `candidate-contract-smoke001`.

## Follow-up: Dynamic keys behind Python reflection aliases

The syntax scan recognizes builtin reflection through same-file import and
assignment aliases. Computed and starred keys now remain visible as review
issues. A named literal initializer is included when it may supply the key.
The file-wide alias match adds candidates and never establishes a binding.

All 236 patchgen tests passed. The 69-case component corpus matched every
expected outcome, recovered 64/65 affected lines and all 24 expected binding
claims, with 27 extra candidates and no extra binding claims. The eight domain
outcomes still matched. Reports are in `aliased-reflection-audit001`.

## Follow-up: Guard unrelated presence changes and measure review warnings

The optional-rename exception now applies only to the synthetic group owned by
the renamed field. The detector rejects a rename that alters another field's
synthetic group through a compiler name collision. The component corpus scores
authored warning lines separately from candidate and binding coverage.

All 237 patchgen tests passed. All 69 component and eight domain outcomes
matched. The component scan found 64/65 affected lines and 24/24 expected
binding claims, with 27 extra candidates and no extra binding claims. All nine
expected warning lines matched. The telemetry smoke adapted with 9/9 affected
lines and zero extras. Evidence is in `presence-companion-audit001`.
