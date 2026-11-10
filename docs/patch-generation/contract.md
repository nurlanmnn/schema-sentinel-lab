# Patch proposal contract 1.0

SS-70 uses `patchgen/fixtures/entity-name-removal/input.json`, pinned to source
`26304c1ed2f4738676a9607e8fe21e17ebd090f0`. This is a manually located example,
not detector or locator output. `python3 -m unittest discover -s patchgen/tests -v`
checks the contract and rejection paths. Validation uses the standard library;
no new Python dependency is required.

| Input field | Meaning |
| --- | --- |
| contract_version | Exactly `1.0`; unknown versions fail |
| change.id/category | Stable case identity and classification; this case is `field_removed` |
| change.old_schema/new_schema | Exact complete schema text before and after; remove field 2 and reserve its number and name |
| change.schema_path | Relative, allowlisted canonical schema file |
| source_revision | Exact 40-character Git commit; branches and stale HEAD are rejected |
| affected_files[].path/language | Existing relative file and `python`, `typescript`, or `csharp` |
| affected_files[].positions | Nonempty list of 1-based inclusive start_line/end_line with reason |
| affected_files[].source_context | Complete file text, checked against the commit and checkout |
| intended_behavior | Required behavior and migration constraints; not a reference implementation |

The source includes construction and decoded-observation reads in Python,
TypeScript and C#, plus the existing round-trip and evidence assertions that must
migrate. Generated bindings are excluded. Positions were inspected against this
commit; the reference inventory repeats them for review. This does not measure
automatic impact recall or constitute a human timing baseline.

Output is a JSON object with `contract_version: "1.0"`, `outcome`, `diff`,
`rationale`, `confidence`, and `assumptions`. Outcomes are `patch`, `no_change`,
or `needs_clarification`. Only `patch` permits a nonempty git-style unified diff.
Rationale is a nonempty explanation. Confidence is a finite number in [0,1],
a subjective model estimate with no calibration claim. Assumptions are strings
identifying unresolved decisions. Non-patch outcomes retain the reason and stop
without creating an application workspace. Missing fields identify the field
in a clear error; invalid proposals exit nonzero and retain a report.

`patchgen/reference/entity-name-removal/expected.patch`, `expected.json`, and
`response.json`, plus `patchgen/oracle.py`, are independent evaluation answers.
They are never loaded by prompt assembly. The prompt allowlists input properties;
tests check that caller-added answer fields do not leak. Existing test source is
provided as migration context; the independent oracle and correct patch are not.

Questions for change-detection and impact-location review:

- Will category names be shared enums, and how will semantic changes be represented?
- Will each input represent one change or a group that must be applied atomically?
- Can the locator supply a commit, full file snapshot, inclusive line spans and language?
- How should uncertain, dynamic, generated, and test impact sites be flagged?
- Who resolves ambiguous intended behavior, compatibility and unknown-field retention?
- How should source movement between detection and proposal generation be refreshed?

The first slice rejects stale context rather than rebasing a generated proposal.


Prompt strategy 2.0 (28 October) retains this public contract. Internally it
requests one JSON response per affected file with outcome, edits (exact before
and after text), rationale, confidence and assumptions. The host converts those
edits to the public unified diff and copies the provided new_schema. Confidence
on the combined proposal is the minimum of the per-file estimates, still
uncalibrated. A file requiring clarification stops the entire proposal. See
`docs/decisions/0002-patch-generator-edits.md` for rationale and boundaries.

Prompt 2.1 adds a complete-file response (`updated_source` instead of edits).
The host creates the diff against the pinned input source. Empty or unchanged
patch outcomes fail; non-patch outcomes cannot contain replacement source. This
changes the internal request strategy, not the public input/output contract.

Prompt 2.2 (current default) instead supplies numbered original source and asks
for inclusive start_line/end_line ranges plus complete replacement lines. The
host rejects out-of-range, overlapping, unchanged and partial-line edits.
Runtime requests omit test-only guidance. Test requests require expected values
to remain unchanged when a negative case corrupts actual data. This retains the
public contract and leaves independent reference answers outside every prompt.

Prompt 2.3 represents replacement text as an array of source lines; the host
adds separators. This replaces prompt 2.2's newline-terminated string format,
which the model did not follow. Each supplied impact line must be covered and
each edit must touch a supplied site. Ranges still refer to the original file;
these checks do not prove semantic correctness or automatic impact recall.


The runtime-only fixture `runtime-input.json` uses the same contract and source
revision but lists only the three runtime files. With the explicit trusted
`entity-name-removal` validation profile, the host applies separately maintained
test changes after the model proposal. These changes are restricted to two test
files and pinned by source, schema and patch hashes. They never enter model
prompts. Reports distinguish runtime generation from independent test migration;
the complete validated review bundle includes both plus regenerated bindings.
The original five-file fixture remains saved and has no passing live result.


Prompt 2.4 (`--strategy migration_edits`) supports removal, rename, explicitly
defined type conversions, and unaffected additive changes. Prompt 2.3 remains
unchanged for earlier replay. [Adapter 1.0](adapter.md) validates structured
producer records; [benchmark seed results](../history/benchmark-seed-2026-10-28.md) distinguish
live failures, a justified runtime no-change, and offline reference validation.
