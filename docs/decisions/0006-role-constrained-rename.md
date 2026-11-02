# Decision 0006: role-constrained rename proposals

Date: 1 November 2026
Status: independent implementation; human review pending

Retain prompt 2.6 and its failed response. Introduce `syntax_rename_roles`,
prompt 2.7, as a separate informed experiment. It uses the same independently
computed descriptors, runtime candidates and validation oracles. One request per
file; no validation feedback, retries or automatic acceptance.

The host derives replacement names from the descriptor event. For TypeScript,
member properties use camelCase. Object keys in an `.encode({...})` argument
also use camelCase. A key in a `fields` variable initializer whose value reads
the same old-named member uses the canonical protobuf name, provided the caller
explicitly states `Runtime observation key becomes` in intended behavior.
That literal policy phrase is a narrow testbed convention, not a general natural
language semantics interpreter. Other TypeScript syntax roles are rejected.
New names must follow the supported lowercase snake_case convention. Python and
C# retain descriptor-derived canonical/Pascal naming from the earlier inventory.

Each edited candidate line must select every inventory token on that line.
Unaffected lines select none. This rejects the missed Python observation key
from the earlier attempt. Lines mixing affected and unrelated old-name tokens
cannot be represented and must be clarified rather than partly edited.

These are syntax-role constraints, not type checking: `.encode` could belong to
another API, a property could belong to another receiver, and `fields` could
have a different purpose. The model still decides which candidate lines change;
semantic mistakes and false unaffected decisions remain possible. Layout and
unselected lines are preserved. Independent builds and value-preservation checks
are mandatory. Confidence remains subjective and human approval remains required.

Acceptance: focused negative tests reject omitted tokens, incorrect construction
names, unsupported object roles and missing observation policy; a mocked request
exercises production request/assembly wiring; an unmodified live attempt is
retained and its actual validation result is reported separately. This does not
establish general model usefulness, type migration, benchmark breadth or human
acceptance. No evaluator answers or trusted test migrations enter the requests.

## Explicit deterministic mode

`deterministic_rename_roles` (`host-rename/1.0`) is a separate proposal mode:
propose every located token with its single allowed descriptor/role-derived name.
It makes zero model requests and does not replay a reference patch. The all-target
candidate assumption is recorded in the proposal; conservative unrelated matches
can cause failure or an incorrect proposal and need validation and human review.
The `confidence` field is zero as an explicit unestimated placeholder, not a
probability. Every token inventory and decision is retained. This is appropriate
for the well-defined syntactic operation; it is not a live model success or an
automatic fallback/repair of a failed response. It must be invoked separately
into a new output directory and runs the same validation gates.
