# Decision 0009: bounded removal and fresh-checkout demo

Date: 2 November 2026
Status: independent implementation; human approval pending

Provide a standard-library `run_demo.py` entry point that checks the tested
Python/tool environment, pinned source ancestry, new evidence directory and free
runtime ports before installing the analysis packages. It launches a separately
selected deterministic policy, the independent pipeline and portable review
export. Setup failures retain logs and a failed report. The launcher never starts
inference or creates a human decision. Dependencies and remote Buf plugins still
require network access; this is not an offline or clean-OS guarantee.

Add `deterministic_remove_name_v1` (`host-remove/1.0`) as an explicit policy for
singular string `simulation.v1.Entity.name`, field 2. Both number and name must be
reserved in the new descriptor. Parse the adopted runtime syntax and delete only
recognized v1 construction/observation items. Python's now-empty dedicated guards
are removed with their sole statements. TypeScript's dedicated observation spread
and final constructor property are removed. C# final initializer entries are
removed. Construction values must be string literals so deleting them does not
discard an arbitrary call's side effects. Unknown uses, guards containing other
work, bindings, non-final initializer items and unresolved candidates reject.

This is bounded source-shape recognition, not receiver/type/data-flow proof.
The adopted bindings can be shadowed by program structures outside the tested
shape; no whole-program safety claim is made. The policy does not generalize to
other fields, schemas, side-effectful constructors, arbitrary branch cleanup or
business semantics. The supplied fixture defines removal semantics; reference
responses and evaluator test migrations are never read during construction.
Confidence zero is an unestimated placeholder. Independent validation and actual
human review remain required. No automatic acceptance or merge exists.

Acceptance: independently computed detector/locator input reaches this strategy;
6/6 known runtime sites are found; compilation, original test categories, relay
round trips, independent retained-field values and a legacy field-2 payload pass;
negative tests reject unsafe/unrecognized shapes; the complete patch and evidence
are exported for review. These tests are not new realistic benchmark cases.
