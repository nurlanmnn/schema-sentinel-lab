# 0020: Bounded inventory integer-width migration checkpoint

Promote the authored inventory width scenario to a buildable int32 -> int64
migration, pinned to baseline `91072d89eb9add6b851a19ac80309a368d671781`.
The descriptor detector classifies the signed field-2 type change. The locator
recovers all nine known producer, observation and predicate lines, with two
conservative request-declaration extras. This remains syntax-candidate recall,
without general receiver/alias/dataflow completeness proof.

`deterministic_inventory_width` accepts only the adopted direct binding shapes
and an explicit decimal-string/ts-proto/strict-stock policy. It changes the TS
producer from Number.parseInt to the exact input string and C# int.Parse to
long.Parse. Python int, decimal-string observations and predicates remain valid.
The policy rejects unknown bindings, numeric JSON requests/observations, changed
predicates, optional/repeated/unsigned fields and unresolved candidate roles.
Confidence is unestimated (zero placeholder); human approval remains required.

The host-owned oracle verifies sixteen valid authored inputs in each runtime,
including signed int64 endpoints and 2^53 +/- neighbors, exact producer bytes,
string-valued decoded quantities and strict >0 stock decisions. Trusted profiles
bind schema and source; no test edits are allowed. Portable reviews retain and
check policy/oracle snapshots and hashes, subprocess evidence and expected cases.
No general malformed-input validation or mixed-version rollout guarantee is made.
Old int32 consumers must migrate before producers emit wider values.

## Evidence

- `pipeline-inventory-width-001`: retained build failure due to unresolved Long
  import at the initial baseline; not a successful migration.
- `pipeline-inventory-width-002` and `review-inventory-width-002`: validated
  deterministic proposal, 48 runtime checks, human decision pending.
- `inventory-width-reference-001`: independently authored known-answer replay
  passes; never counted as model generation.
- `inventory-width-number-negative-001`: TS Number(...).toString() compiles and
  passes the original Entity checks, but the independent oracle rejects case 12
  (9007199254740993) after the 16 Python checks. Its review is approval-ineligible.
- Unit logs: `inventory-width-patchgen-final-001` (137 passing) and
  `inventory-width-testbed-final-001` (27 passing). The earlier suite-unit log
  retained an outdated six-case expected-total assertion; the corrected final
  suite expects seven distinct cases and 54 known lines.

The suite now includes this seventh distinct migration, retains previous runs
unchanged, and supports `run_demo.py --case inventory-width --local-codegen`.
The user subsequently prioritized live LLM evaluation/model assessment. Do not
expand deterministic cases further before that milestone. Seven deterministic
migrations do not establish live-model patch success or meet the twenty-case MVP.
