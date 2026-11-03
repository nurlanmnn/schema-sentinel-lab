# 0027: Bounded TypeScript source-binding evidence

November 3, 2026. Extends the separate positive-evidence boundary from decision
0025 without upgrading lexical candidates to whole-program type proof.

An explicit policy maps the four repository schema-path/message-FQN pairs to
standard ts-proto 1.165.0 emitted module paths and codec symbols. Relative source
imports are normalized against the runtime's repository path and must match the
declared generated path exactly. Named/namespace imports and their aliases are
supported. Type-only, default, re-exported, wrong-version, path-mapped and unknown
imports do not establish a codec. This is not filesystem/runtime import validation.

The layer follows immutable `const` aliases, direct standard `Codec.decode(...)`
results, direct member/string-key reads and literal object keys supplied to
`Codec.encode({...})`. Functions/arrows are analyzed separately from stable import
identities; parameter and enclosing lexical shadowing invalidate those identities.
It does not propagate outer local values into closures. Mutable `let`/`var` flow,
branch joins, destructuring, casts, annotations and inferred interface compatibility
never establish a message value. Exact original UTF-8 token ranges are retained.
Field-name conversion is restricted to the declared ASCII lower-initial camel/snake-case policy.

A conservative AST hazard pass covers aliases and mutations in unsupported bodies.
Visible codec writes, const reassignments, native namespace mutator references
(including bracketed/aliased forms), eval/Function, TypeScript namespaces/ambient
scopes and dynamic `with` disable positive evidence. Scope-conflated rejection
sets may suppress valid claims. The policy assumes standard generated codecs and
no arbitrary runtime monkeypatching; it is source provenance, not execution proof.

The shared binding dispatcher is used by locator and adapter. The adapter recomputes
Python and TypeScript claims, rejects altered/stripped evidence and missing required
rename/removal lines/files, and keeps type-change references optional. Existing
line-level candidate-review gates and `-binding1` payloads now carry TS evidence.
They do not prove every field token was transformed. C# remains candidate-only.

Corpus-only policy overrides are explicit fixture assumptions, as for the existing
Python corpus; the adapter does not accept them as repository policy. Historical
source/evidence snapshots remain intact. No dependencies or model requests were added.

Required edits now distinguish source identity from generated member changes.
Under default ts-proto key naming, `speed_mps -> speedMps` preserves `speedMps`.
The bound TS reference is optional in this case; Python still needs the rename.
Removal remains required, and a rename with two known distinct generated names
remains required. Unsupported new spellings leave the edit requirement unresolved
and record a limitation. A shared rule governs locator flags and adapter checks
for both positions and omitted files. A local protoc/ts-proto fixture confirms
the unchanged member, without model inference or external generation.

The rejection-only alias set now follows visible class/codec values through
containers, indexing, properties and conditional/boolean expressions before
checking writes. It does not establish receiver types through those forms.
Call results are excluded so constructor/decoder instances do not become class
aliases, and ordinary instance-field writes retain their source evidence. Unknown
call effects and arbitrary monkeypatching remain outside the declared policy.
