# 0025: Separate syntax candidates from bounded Python binding evidence

November 3, 2026. Implements the first hardening step under decision 0024.

All active locator positions now use `resolution: candidate`. Completion means
that the declared syntax scan ran without blocking issues; it does not establish
that every match belongs to the changed message. The adapter still reads legacy
`resolved` fixture records as candidates for historical replay compatibility.

A separate Python layer can attach positive source evidence under an explicit
standard generated-module policy. The current repository policy maps exact
schema paths and message FQNs to the modules emitted from the `proto` Buf root.
Matching a similarly named import or a different schema version is insufficient.
An absent mapping produces candidates without binding claims.

The bounded layer follows direct imports (including aliases), module imports with
an alias, generated message constructors, class `FromString`, and straight-line
local assignments. Each bound token records its import/assignment chain and
one-based UTF-8 byte columns. Function parameters and whole-function lexical
shadowing invalidate inherited bindings. Branch assignments, comprehensions,
nested functions, annotations, wildcard imports, namespace mutation and arbitrary
cross-function flow do not establish receiver identity. Unknown sites are retained
as syntax candidates. Namespace hazards can disable all positive evidence for a
file. The policy assumes standard generated modules and no runtime monkeypatching;
it is not runtime import resolution or a claim of whole-program certainty.

For rename/removal events, bound field references get `required_reference: true`.
The adapter preserves this evidence. Candidate-review resolvers reject an
`unaffected` decision for those lines; `needs_clarification` remains available.
Unbound candidates may still be unaffected with rationale. Prompt payloads carrying
these flags get a `-binding1` suffix; frozen historical payloads keep their version.
This enforces line-level review coverage, not proof that a token was transformed
correctly. Compilation, semantic validation and human approval remain necessary.
Type changes are not automatically forced to edit every field access.

The detector also preserves named field-type identity and distinguishes
`no_structural_change`, unsupported structure and multiple events. Enum defaults,
existing value order and the first alias for a number cannot silently change.
Reservations may track retired names/removed numbers; unrelated reservation edits
are unsupported. Comments, units, frames and intended behavior remain explicit
semantic policy, never inferred from field names.

The new 26-case source corpus and descriptor boundary regressions are component
evaluation, not twenty validated migrations. See the measured checkpoint in
`docs/deterministic-analysis-2026-11-03.md`.
