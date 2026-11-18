# Decision 0044: accept whole-line edits missing only the final line break

Status: accepted by the user on 2026-11-18. This revises how the 0041 locked
configuration is scored. The model, prompts and sampling are unchanged.

## Change

`patchgen/anchor_edits.resolve`: if an edit's `before` text does not end in
`\n`, and `before + '\n'` occurs in the source, the resolver uses
`before + '\n'`. It then also appends `\n` to a nonempty `after` that lacks
one. Nothing else is normalised. Partial lines, other whitespace differences,
`\r`, and the exactly-once match rule are still rejected (tests in
`patchgen/tests/test_anchor_edits.py`).

## Why

The 0043 investigation found that 23 of the 26 retained rejections with
"before must contain complete source lines" were exact whole lines missing
only the final line break (Gemma 10, North Mini Code 9, gpt-oss 3, Laguna 1).
Gemma lost every `inventory-state-bool` fresh attempt this way, and the repair
loop could not recover, because the message did not name the missing newline.
In an offline replay, appending only that newline let all three recorded answers
pass full validation. A trailing line break carries no meaning in these edits,
so rejecting it measured formatting, not migration ability.

## Fingerprints

`LOCKED_PROMPT_SHA256['protocol']` hashes the resolver source, so it changes
from `b6fa3513…` to `6f648b9c…`. The `one_shot` and `repair` prompt hashes are
unchanged (verified). Evidence produced before this decision records the old
protocol hash and keeps its measured scores.

## What this does not claim

- No score has been measured under this rule. The 12/15 fresh figure in 0043 is
  a post-hoc counterfactual on cases already seen. Do not quote it as a result.
- The fresh screen cases are spent. The fresh manifest now refuses runs
  because sealed code changed, which is intended.
- The effect must be measured on cases not used to find it: the unspent
  held-out set (H1–H8, `held-out-plan.md`), which still needs an independent
  evaluator.
