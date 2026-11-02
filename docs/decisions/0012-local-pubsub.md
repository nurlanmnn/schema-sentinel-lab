# Decision 0012: bounded local pub/sub testbed

Date: 2 November 2026
Status: implemented and locally exercised; real human acceptance pending

Add a separate pull-based in-memory fan-out broker, bound to loopback on an
OS-assigned port. The existing HTTP relay and pinned migration fixtures remain
separate. Python, TypeScript and C# subscriber modes reuse their actual
`process_entity`/`processEntity`/`ProcessEntity` decoders. No new dependency.

The topic registry binds `entity.v1` to `simulation.v1.Entity` at
`proto/v1/entity.proto`, and `entity.v2` to `simulation.v2.Entity` at
`proto/v2/entity.proto`. Publishers supply opaque protobuf payloads encoded in
base64 for HTTP JSON transport. The broker never decodes fields or constructs
observations; registered subscribers choose the decoder by the registry version.
The runtime independently returns decoded fields in its acknowledgement.

## Local HTTP contract

All successful responses are JSON objects. POST bodies are JSON objects, at most
64 KiB. Invalid requests return 400; unknown routes return 404. No authentication:
this is a loopback-only test harness, not a production multi-user service.

- `GET /state`: topic registry, subscriber inventories, pending message IDs,
  publication records (including payload SHA256), and acknowledgement records.
- `POST /subscribe {subscriber, runtime, topics}`: unique short subscriber ID,
  one of the three runtime names, nonempty unique registered topics. Duplicate
  IDs reject; subscription changes/unsubscribe are unsupported.
- `POST /publish {topic, payload}`: registered topic and strict base64 string.
  Atomically queues one immutable delivery for every current matching subscriber;
  returns global increasing message ID and recipient IDs. Zero recipients is
  valid; there is no historical replay for later subscribers.
- `POST /poll {subscriber}`: first unacknowledged delivery, including message ID,
  topic, schema version and payload, or `delivery: null`. Polling does not remove
  it; repeated polling before ack returns the same delivery.
- `POST /ack {subscriber, message_id, fields}`: accepts only the subscriber's head
  delivery and a string-to-string observation dictionary. Records the observation
  and monotonic publish-to-ack latency, then removes that subscriber's head.
  Unknown, duplicate or out-of-order acknowledgements reject without mutation.

Queues are FIFO per subscriber. No timeout/retry scheduler, lease, dead-letter
queue, persistence, restart recovery, broker-side payload validation, producer
runtime, or exactly-once claim. Subscribers fail on decoder/HTTP error and the
runner detects failure; an invalid payload can block its queue. Poll redelivery
is explicit but automatic recovery is not implemented. State is capped to 32
subscribers and 256 publications per run; payload limit is 32 KiB after decoding.

Acceptance: real processes in all three languages subscribe to both topics;
four independently wire-encoded v1 and four v2 inputs (empty, ASCII, Unicode,
escaped strings) reach all matching subscribers with identical expected fields.
Topic isolation, no historical replay, repeated polling, independent queues,
out-of-order/duplicate ack rejection, malformed requests and invalid topics are
checked. Evidence includes payload hashes, observations, tools/source identities,
subscriber logs and timing scope. Publish-to-ack includes polling/decoding/HTTP;
it is not schema propagation time or a human baseline. Existing relay and patch
validation must still pass. No generated patch is approved by these tests.

## Retained evidence

`patchgen/evidence/pubsub-local-002` passed all 8 publications / 24 independent
decoder acknowledgements across two versioned topics. `pubsub-local-001` is the
retained initial C# failure: PostAsJsonAsync used chunked transfer while the
contract requires Content-Length. The subscriber now sends bounded StringContent.
The 19 testbed unit checks, all 104 patch-generation checks and original 4 relay
roundtrips passed. These eight inputs are transport/conformance samples, not eight
new schema-change benchmark cases. Runtime proposals remain unapproved.
