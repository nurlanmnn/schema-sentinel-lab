# Local patch review

Analysis rejected at the detector, locator or adapter gate can also be exported
after source identity and analysis records are retained. Such a review shows
`analysis_rejected`, includes the minimal request and blocking report, and permits
rejection only. Generation and validation remain `not_run`. Early malformed
requests or descriptor-build failures may terminate before review export.

Run the bounded type migration and export a portable review in one command:

```sh
.venv/bin/python -m patchgen.pipeline --fixture patchgen/fixtures/v2-identifier-bytes/runtime-input.json --output patchgen/evidence/my-type-run --generate --strategy deterministic_utf8_v2 --review-output patchgen/evidence/my-type-review
```

All output directories must be new. The review directory must be outside the
pipeline evidence directory. For a previously retained proposal run:

```sh
.venv/bin/python -m patchgen.review export --run patchgen/evidence/pipeline-type-deterministic-001 --output patchgen/evidence/my-review
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory patchgen/evidence
```

Open `http://127.0.0.1:8765/my-review/index.html` in a browser. The server is local
only. Read intended behavior, exact revision, proposal mode and complete patch;
follow the evidence links to inspect validation details. A passing validation
result still requires human review. Failed proposals allow rejection only.

Enter your name and rationale, acknowledge review of the complete bundle, then
export the desired decision. The downloaded `review-decision.json` contains the
manifest identity, source revision, decision, reviewer, rationale and timestamp.
Keep it with the review bundle. No code is applied or merged by the page.

Verify the decision against the unchanged exported evidence:

```sh
.venv/bin/python -m patchgen.review verify --bundle patchgen/evidence/my-review --decision /absolute/path/to/review-decision.json
```

Verification detects changed artifacts and mismatched decisions. Records are
self-reported and do not authenticate a reviewer. This is a local review interface,
not a multiuser approval system or deployment gate. Decision 0008 records the
scope. No real human approval has been recorded by automated tests.

## Retained checks

- `review-type-001`: portable export of the validated deterministic type proposal.
- `review-rejected-001`: failed live rename proposal; approval disabled.
- `pipeline-type-review-001` / `review-type-integrated-001`: passing one-command
  detector → locator → deterministic proposal → validation → review export.
- `review-ui-synthetic`: clearly synthetic browser rejection/download/verification;
  its `test-only-decision.json` is not human acceptance of a project patch.
- `review-tests-002.log`: full suite passes 82 software tests, including artifact
  tampering, stale revision, failed approval and injected-text rejection checks.
