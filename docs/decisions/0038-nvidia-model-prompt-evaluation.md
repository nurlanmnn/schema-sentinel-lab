# Decision 0038: bounded NVIDIA model and prompt evaluation

Evaluate public synthetic migrations through NVIDIA's direct hosted API, with
explicit model allowlists and no fallback. Keep the original prompt and its
failure evidence. Do not edit acceptance oracles or remove checks to improve
reported results.

Initial Ultra trial: one validated rename, one rejected exact float observation.
The first eight-case Ultra comparison gave 2/8 for prompt 2.5 and 4/8 for 3.0.
Many failures were unchanged edits. Super 3.5 returned an undocumented private
model identifier; exclude those calls from model-quality inference and stop
that route. Identity errors now stop the case and cohort as provider failures.

A finite follow-up compares Ultra and Google Gemma 31B on eight eligible cases
using semantic exact-block prompt 3.1. Provider-recommended sampling is explicit.
All prompts are development variants informed by existing benchmark failures;
no unseen-case reliability or statistical significance is claimed. Twelve cases
remain outside the live route. Human approval is required even for passing
patches, and no benchmark patch is merged automatically.

Keep prompts, transport source, raw outputs, host resolutions, validation
results, and review bundles in fresh evidence directories. Stop after the two
follow-up cohorts and report outcomes and limitations rather than adding an
unbounded succession of prompt variants.

## Observed outcome

The final development comparison is complete:

- Ultra original line prompt 2.5: 2/8 validated.
- Ultra semantic line prompt 3.0: 4/8 validated.
- Ultra semantic block prompt 3.1: 5/8 validated, combining six initial completed
  cases with two fresh case attempts after one HTTP 502 interruption.
- Google Gemma 31B through NVIDIA, semantic block prompt 3.1 and bounded JSON
  envelope parsing: 6/8 validated. Its initial strict-envelope attempt is kept
  separately and incomplete.

Recommend explicit Gemma/3.1 selection for the next accuracy-focused evaluation;
Ultra/3.1 is faster in this sample. Keep CLI defaults unchanged and require all
validation gates. Do not claim statistical significance, held-out reliability,
full twenty-case live coverage, or human acceptance. See
`patchgen/evidence/nvidia-evaluation-001/summary.md` for the comparison and limits.
