# Decision 0013: validate bounded proposals through pub/sub

Date: 2 November 2026
Status: independently validated in the Lab; real human review pending

Keep the original historical fixtures unchanged. Add three explicitly named
`pubsub-name-rename`, `pubsub-name-removal` and `pubsub-identifier-utf8` fixtures,
initially pinned to the typed-envelope pub/sub baseline a65e45f. Decision 0014
updates the active fixtures to the bounds-checked TypeScript baseline 6ead28a. These repeat the same three
Entity schema mutations on a transport-capable baseline; they are not three new
domain changes or evidence of a twenty-case benchmark.

The C# envelope uses typed records because generic JsonElement.GetProperty calls
trigger the locator's conservative reflection warning. That warning remains
unchanged. The first new rename run at da98c2a is retained as analysis-rejected;
no proposal or inference ran. The first typed-envelope baseline exercise also
retains an intermittent premature HTTP-response failure. Responses now explicitly
announce Connection: close; a subsequent baseline run and five sequential repeats
passed. These repeats do not establish broad transport reliability or prove the
root cause of the earlier transient failure.

The three new evaluator-owned validation profiles bind exact source commit,
change ID, new schema hash, original two-file test migration (rename/removal),
and explicit semantic/oracle selection. UTF-8 makes no test-source changes.
Only the named profile registry can select checks. All continue to run Buf,
TypeScript/.NET builds, original relay tests and independent semantic oracles.
They additionally run an immutable copied pub/sub harness against the actual
built proposal workspace. The harness never edits runtime sources or trusts
runtime-returned fields as expected answers. The proposal generator never reads
reference patches or pub/sub expectations and makes zero model requests.

Four v1 plus four v2 payloads are wire-encoded without generated Python bindings.
Rename preserves field-2 values under display_name observations; removal sends
legacy field-2 bytes but requires observations to omit name; UTF-8 preserves
valid textual identifiers under the v2 string-to-bytes policy. Both topic versions
must reach each runtime independently and in order. Standard oracles also check
the generated schema field types, since UTF-8 string and bytes share wire shape.
Invalid UTF-8, mixed schema-version subscribers and broker recovery remain out
of scope. The broker does not validate protobuf content.

The review exporter copies and hashes pub/sub report, expectations, broker state,
three runtime logs and three harness source files. Passing pub/sub reviews
require all these artifacts, matching evaluator hashes, matching result identity,
24 decoded deliveries and stopped-child/broker flags. Verification enforces the
same requirements. Historical reviews keep their earlier scope; no retained
bundle is silently edited. Static review UI assets are unchanged.

Acceptance evidence:

- `pipeline-pubsub-rename-002`, `pipeline-pubsub-removal-001` and
  `pipeline-pubsub-utf8-001`: all pass prior checks plus 8 publications / 24
  independent acknowledgements each. Six known runtime lines recovered per case;
  UTF-8 retains three conservative unchanged-v1 candidates.
- `review-pubsub-{rename,removal,utf8}-001`: complete new review snapshots.
- `demo-pubsub-utf8-001`: one-command setup/pipeline/review entrypoint passes.
- Profile identity/semantic-selector checks and missing/tampered pub/sub review
  evidence reject in synthetic tests. No synthetic decision represents human
  acceptance. Publication-to-ack timing is not schema propagation or human time.
