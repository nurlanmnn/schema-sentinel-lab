# Decision 0002: assemble patches from file-scoped model edits

Date: 28 October 2026
Status: local implementation for review

Updated: prompt 2.1 adds complete-file proposals after exact-anchor failures.

The first local generation requested a multi-file unified diff directly. The
3B model supplied malformed patch headers and omitted runtime changes. The next
strategy requests exact text edits for one affected file at a time. Each request
receives the supplied schema change, intended behavior, manually located impact
positions and that file's original source. It does not receive reference answers,
other model responses or validation feedback.

The local Ollama request uses a JSON schema for outcome, edits, rationale,
confidence and assumptions. Before/after anchors must match the original source
exactly once and must not overlap. The host assembles a unified diff with Python's
standard-library difflib. It copies the authoritative supplied new_schema into the
proposal; the model is responsible for runtime/test migrations, not redetecting
or designing the schema change. Bindings still come only from `buf generate`.

The public input/output contract remains 1.0. Prompt strategy is 2.0. Every run
retains requests and raw responses by file, exact model metadata and settings,
implementation snapshots, failures and validation evidence. A run issues one
request per input file. It never repairs responses or retries based on validation.
Any rejected file blocks assembly; any clarification blocks partial application.
A validly formatted proposal may still fail compilation or behavior checks.

The migrated tests must retain their original test names. An independent oracle
also calls their evidence validator with deliberately invalid observations,
identifiers and traces. Passing self-edited tests alone is insufficient.

`--prepare-source` explicitly creates a detached snapshot at the fixture commit,
so the example runs in one command from the implementation checkout. Without
that flag, the existing exact-HEAD/context checks still reject stale source.
Neither path changes the original checkout or merges the proposal.

Model-origin constraint remains open-source and non-Chinese. The existing 3B
model is retained for failure evidence; one additional candidate, Mistral AI's
Ministral 3 8B Instruct 2512, was selected for a bounded local evaluation. Its
Ollama Q4_K_M artifact is listed at 6.0 GB and model license is Apache 2.0. On the
16 GiB M4, unload other models and use a bounded 16,384-token request context.
This is a testable capacity choice, not a claim that larger models always work
or a final team-wide architecture decision. Evaluation results are reported
separately; old attempts are not rewritten.

Sources:

- https://docs.ollama.com/capabilities/structured-outputs
- https://ollama.com/library/ministral-3:8b
- https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512

Automatic detector/locator integration, a multi-case benchmark, calibrated
confidence, repair loops and human acceptance remain separate work.


## Complete-file strategy (prompt 2.1)

The 3B model failed exact anchors in a runtime file; the 8B model covered the
runtime edits but still invented indentation and source substrings in test
anchors. These remain failed attempts. The default strategy now requests a
complete `updated_source` for each file. The host still owns the file path and
unified diff; the model cannot create, rename or edit an unlisted file.

Use `--strategy exact_edits` to retain the prompt-2.0 strategy for comparison.
Use `--strategy file_content` (default) for prompt 2.1. Each strategy retains one
response per file without a repair loop. Returning full files removes the anchor
copying requirement but may change more unrelated text, so diff review and
independent validation remain mandatory. `no_change` and `needs_clarification`
responses carry an empty updated_source; they cannot smuggle a partial edit.


## Line-range strategy (prompt 2.2)

Full-file output preserved an invalid C# Name initializer and invented a test
field. That attempt failed compilation and remains saved. The default now uses
small inclusive line-range edits against explicitly numbered original source.
This avoids both exact-anchor copying and unnecessary whole-file rewriting.
All ranges are checked before assembly. Removed properties must disappear even
when their old values were empty; aliases and new fields are forbidden.
Test-specific guidance is supplied only for test files. This is another saved
configuration experiment, not a repair of earlier raw responses or a claim of
first-attempt success. No automatic feedback/repair loop was introduced.


## Line arrays and impact coverage (prompt 2.3)

The prompt-2.2 responses found useful line ranges but omitted required terminal
newlines, and one test response included a no-op while missing an impact site.
That run remains failed. Prompt 2.3 represents replacement lines as a JSON array,
letting the host serialize line boundaries. It also checks that every supplied
impact line is covered and that edits touch supplied sites. This is a protocol
change, not manual correction of a saved response. The independent oracle now
requires the four retained-field fixture cases to still cover empty, Unicode
and escaped strings. Their original values may be moved into a retained string
field to preserve the categories after deletion of a field.


## Keep evaluator-owned tests independent

The 8B runtime edits passed edit checks, while attempts to generate test changes
continued to miss sites or weaken negative cases. The working slice now uses a
runtime-only input and an explicitly selected, versioned validation profile for
the test migration. The profile is independent reference data, not model output,
and is excluded from prompts. It is restricted to two test files and pinned to
the exact source, schema and test-patch hashes. The model cannot select a profile
or edit these test files. No saved model response is corrected or cherry-picked.

`proposal.patch` contains model runtime changes plus the schema copied from
input. `validated.patch` also includes independently maintained test changes and
regenerated bindings and is the complete human-review bundle. Passing this path
establishes runtime patch generation against trusted tests; it does not establish
that the model can migrate tests. The broader fixture and all failures remain.
