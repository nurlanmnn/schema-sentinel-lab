# Decision 0005: bounded syntax-token rename proposals

Date: 1 November 2026
Status: independent experiment; human review pending

Line-edit prompt 2.5 failed both live rename and type cases. Candidate review
improved the mechanical boundary but did not prevent the model from misreading
version branches or generating invalid/duplicate review records. Preserve those
attempts. Do not silently repair their responses or call them successes.

Add an explicit rename-only strategy, prompt 2.6 (`syntax_rename`). Rebuild the
same-identity schema descriptors and require exactly one field_renamed event.
Enumerate syntax identifier/string tokens on the already located candidate
lines. The model selects token ids and descriptor-derived replacement names,
with one edit/unaffected review per candidate line. The host replaces those
byte spans and leaves other source text, indentation, guards and layout intact.
The model still decides which tokens need changes and, in TypeScript, whether a
property uses a canonical observation key or generated camelCase name.

This is a hybrid proposal strategy: descriptor/AST constraints plus model choices,
not unconstrained LLM source generation. The host rejects unknown/duplicate ids,
unsupported names, missing candidate reviews and inconsistent edit decisions.
It does not prove model choices or semantic coverage correct. A missed token,
wrong TypeScript observation name, or incorrect affected/unaffected decision may
still fail compilation or runtime validation. Human review remains required.
The existing independent test migration and runtime oracles are unchanged.

The strategy is intentionally limited to a single field rename and the adopted
parser languages/naming conventions. It cannot remove fields, add conversion
logic, repair guards, or handle arbitrary semantic migrations. Unsupported input
is rejected. First-pass 2.5 failures and the new 2.6 attempt are separate evidence;
there is no validation-feedback repair loop. Small selected fixtures and informed
prompt changes do not establish an unbiased general model success rate.
