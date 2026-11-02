# Decision 0014: reject truncated payloads before pub/sub acknowledgement

Date: 2 November 2026
Status: independently exercised; real human acceptance pending

A process-level negative control published `0a0561`: field 1 declares five bytes
but only one byte follows. `pubsub-malformed-001` retained an actual divergence:
Python/C# rejected it, but the TypeScript BufferReader clamped string length to
the available bytes, observed entity_id `a`, and acknowledged. The control timed
out and failed; it is not counted as conformance success.

The TypeScript processor now copies input to a plain Uint8Array before invoking
the same generated decoder. In the pinned protobufjs 7.6.6 source, Reader.string
uses a bounds-checked bytes method while BufferReader.string clamps its end to
the available buffer. This small normalization selects the checked path for
Buffer and plain-array callers. No generated code or dependency version changes.
This addresses truncated length-delimited values; it is not a general wire
validator or a claim about invalid UTF-8, every malformed tag, or unknown fields.

`pubsub-malformed-002` records nonzero exits in all three actual subscribers,
zero acknowledgements, the same pending head in each queue and clean shutdown.
The harness now also requires runtime-specific protobuf decoder error signatures
in every subscriber log, so an unrelated HTTP/process error cannot by itself
satisfy this control. Valid samples still pass (`pubsub-after-malformed-002`).
`pubsub-typescript-decoder-001.log` exercises Buffer/Uint8Array, v1/v2,
truncated/complete inputs against the actual compiled processor.

The active three pub/sub fixtures now pin 6ead28a, which includes the decoder
fix. Source inventories were reinspected for shifted TypeScript lines. The
historical cases and previously exported bundles keep their original revision
and scope. A fresh proposal must pass both valid fan-out and the truncated-v1
negative control. The latter status is `expected_rejection_observed`, with zero
decoded deliveries; it is never called a successful migration or delivery.
The review bundle includes its six artifacts and verifies result identity,
nonzero subscriber exits, decoder-error evidence and cleanup. No recovery or
replay is performed: subscribers stop and the runner cleans up. This is a local
failure boundary, not production reliability or broker fault tolerance.

Latest full runs: `pipeline-pubsub-rename-004`, `pipeline-pubsub-removal-003`,
`demo-pubsub-utf8-negative-003`. Each includes the prior gates, eight valid
publications / 24 decoded acknowledgements, and one rejected truncated payload
with all three decoder failures. Review exports are new complete snapshots.
`demo-pubsub-utf8-negative-001.log` is a retained preflight refusal while another
owned validation run still held port 8000; it created no demo output directory.

The active profile names this stronger evidence requirement
`truncated_v1_decoder_logs`. Earlier `truncated_v1` snapshots retain their
exit/queue-only scope and remain verifiable; the current verifier requires
explicit decoder signatures for the new profile. The new generation gate cannot
select the historical weaker profile. Unit checks cover both scopes.

Final local checks: 109 patch-generation tests and 21 testbed tests pass.
`demo-pubsub-rename-negative-001` also passes with the current explicit
`truncated_v1_decoder_logs` profile and complete review export. No service is
left running after these checks.
