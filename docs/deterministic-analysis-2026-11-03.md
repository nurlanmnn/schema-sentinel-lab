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
see [decision 0025](decisions/0025-bounded-python-binding-evidence.md).

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
