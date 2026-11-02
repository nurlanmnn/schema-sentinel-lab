# Decision 0007: explicit bounded UTF-8 type migration

Date: 2 November 2026
Status: independent implementation; human approval pending

`deterministic_utf8_v2` (`host-utf8/1.0`) explicitly selects the valid-UTF-8 text
policy for singular `simulation.v2.Entity.entity_id`, wire field 1, string to
bytes. Descriptor detection must confirm exactly this event. Repeated, optional,
oneof and other field/type/message changes reject. This is a narrow supported
operation, not automatic semantic inference or a general type migration engine.

The adopted Python, TypeScript and C# parsers find constructor and observation
expressions by syntax. Existing literals are preserved, with UTF-8 encoding only
on v2 construction and decoding only on v2 observations. TypeScript uses encoder/
decoder instances; C# uses ByteString.CopyFromUtf8 and ToStringUtf8. Shared Python
and TypeScript observations use explicit version branches. Known v1 construction
and observation candidates are recorded unchanged, including conservative locator
extras. Unknown bindings, roles or unhandled candidate lines reject the proposal.
All edits retain original byte spans, before/after text and role decisions.

Recognition is deliberately tied to the adopted small testbed dispatch/binding
shapes, including its variable and import conventions. It is not receiver/data-flow
proof, alias resolution or arbitrary control-flow analysis. Shadowing and modified
program structure need separate support and tests. The CLI strategy explicitly
selects the conversion semantics; prose is not interpreted as conversion rules.
Arbitrary non-UTF-8 bytes and mixed-version interoperability remain out of scope;
no cross-language invalid-byte behavior is claimed. Confidence is unestimated,
represented by zero with that qualification in assumptions.

No model calls, answer replay, automatic repair, acceptance or merge occur. The
same independent validator checks regenerated bindings, runtime builds, existing
unit/round-trip tests, and four UTF-8 v2 payloads decoded/reencoded in every
language. Runtime samples and v1 behavior must remain unchanged. Human review
must accept the supplied semantics and complete validated bundle separately.
