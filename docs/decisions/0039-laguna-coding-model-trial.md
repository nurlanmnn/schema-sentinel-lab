# Decision 0039: frozen-prompt Laguna coding-model trial

At the user's request, evaluate Poolside Laguna XS 2.1, a coding-focused model
served through NVIDIA's direct hosted endpoint. The model is explicitly
allowlisted as `poolside/laguna-xs-2.1`; no model/provider fallback is enabled.
NVIDIA's published endpoint and parameters were checked on 5 November 2026:
https://build.nvidia.com/poolside/laguna-xs-2.1

Use the existing frozen `candidate_semantic_blocks` prompt 3.1, source revisions,
exact block resolver, bounded JSON-envelope parser, compilation/unit tests and
independent runtime oracles. Do not tune prompts or acceptance checks after
observing Laguna results. One sample per each of the eight live-eligible authored
migrations; no repair loop, manual patch substitution, or automatic retry.
Retain failures and provider problems separately. Human approval remains required.

Use temperature 1 and top_p .95 as in NVIDIA's example, with the same 4096 output
token budget as the preceding Gemma and Ultra trials. Do not send Nemotron-only
chat-template flags to Laguna. This compares complete configurations, not a
controlled change of model parameters alone. The provider sample uses an 8192
output budget; this trial deliberately keeps the shared smaller comparison budget.

Connectivity probe and implementation tests are separate from model patch
validation. The eight cases were used in earlier prompt development, so results
are not held-out generalization evidence or a full twenty-case live benchmark.
The previous best observed configuration was Gemma 31B at 6/8; compare Laguna
without reclassifying historical failures or treating human review as complete.

Evidence: `patchgen/evidence/nvidia-laguna-xs21-001`.
