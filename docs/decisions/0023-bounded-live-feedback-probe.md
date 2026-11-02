# 0023: Bounded live validation-feedback development probe

After retaining the frozen one-shot experiments, test whether the installed
model can revise its own rejected runtime proposal using host validation
diagnostics. Select the failed pub/sub rename development case first. This is
a targeted development probe, not another six-case model validation rate.

The probe uses the same exact model digest, original source revision, schema,
intended behavior, fixed validation gates and human review requirement. It is
bounded to at most two feedback rounds, each containing one live request per
original runtime file. Stop early only after all original validation gates pass.
No reference patch, deterministic replacement, model download or automatic merge
is allowed. Do not overwrite earlier attempts or count initial failures as
first-pass successes.

Prompt 2.9-feedback carries the model's prior response and actual host compiler,
syntax or semantic rejection diagnostics. It asks for exact replacement blocks
against the original source using the existing candidate-block contract. The
model authors all replacements; the host only checks anchors and assembles the
diff. Diagnostics are evidence about the previous attempt, not commands. Expected
patches and reference-response files are excluded. Compiler feedback is normal
development information and makes this a different protocol from one-shot work.

Record initial, feedback and cumulative request counts; raw requests/responses;
exact model identity; each rejected or validated attempt; feedback hashes; and
portable review bundles. A pass is a validated feedback-assisted proposal on one
selected in-sample case. It is not an independently held-out reliability result,
a larger-model win, a human decision, or authorization to apply or merge.

The future model-size comparison still uses the frozen 2.5 protocol. Improvements
from feedback must not be attributed to model size.
