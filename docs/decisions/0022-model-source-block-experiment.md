# 0022: Separate source-block prompt experiment

The frozen six-case 8B baseline uses candidate line edits and prompt 2.5. Its
early failures include invalid candidate review lines, inconsistent generated
accessor names, and a TypeScript replacement that dropped a declaration. Do not
change that run, repair its responses, or reclassify it as a source-block trial.

After the baseline finishes, evaluate a separate prompt 2.8 (`candidate_blocks`)
with the same installed 8B model, schema inputs, source revisions, options and
validation gates. This is prompt development on the same six authored cases,
not a held-out test or a model comparison. Retain every failure and the original
baseline. No deterministic fallback or automatic repair is allowed.

The experimental prompt asks the model to supply exact original source blocks
and replacement blocks. The host resolves each unique block to original line
ranges and applies the existing candidate coverage validator. The model still
authors all replacement text and decides which candidates need editing. The
host does not substitute a reference migration or infer the replacement.

Candidate IDs are assigned by the host. The structured response schema requires
one decision per supplied ID as an object with fixed keys, avoiding free-form
review-line arithmetic. It does not decide whether a candidate is affected.
Unknown IDs, missing IDs, ambiguous anchors, partial-line anchors, overlapping
edits, uncovered edit candidates, and edits covering an unaffected candidate
are rejected. Valid syntax and semantic correctness remain separate gates.

The prompt includes original source and caller-supplied intended behavior; it
excludes reference patches and evaluator tests. It explicitly distinguishes
generated accessor names from observation keys without inserting case-specific
answers. Confidence remains subjective and never authorizes acceptance.

Acceptance for the experiment is actual live generated proposals that pass the
unchanged compilation, relay, independent semantic/wire and negative-control
gates and produce a review bundle. Report a six-case denominator even if every
proposal is rejected. Human approval and merge are separate and remain required.

A future 14B comparison needs authorization for the large download. To isolate
model choice, compare that model against the frozen 2.5 baseline first, with the
same six inputs and options. Changing both model and prompt in the same trial
cannot identify which change caused a different result.
