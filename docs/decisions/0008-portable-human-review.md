# Decision 0008: portable local human review

Date: 2 November 2026
Status: independent implementation; real human acceptance pending

Export a local static review page and copies of allowlisted evidence files. Show
intended behavior, proposal mode/strategy, exact source revision, validation status,
the complete validated patch when available, and links to retained evidence.
The page runs without external assets, a new framework, authentication or a
remote service. No dependency adoption or external publication is needed.

Every exported evidence file has a SHA-256 hash and byte count in manifest.json.
A reviewer supplies their name, rationale and complete-bundle acknowledgement,
then downloads an approval or rejection record tied to that manifest hash.
Approval is disabled unless the report says validation_passed and a nonempty
complete patch exists. Rejections can be exported for failed proposals. The CLI
verifier rechecks manifest identity, all artifact hashes, source/change identity,
required reviewer fields and approval eligibility. It never applies code.

This is a self-reported decision record, not authenticated reviewer identity,
a cryptographic signature, an authorization service or proof of human attention.
An attacker who can rewrite both manifest and decision can forge a new record;
trusted transport/storage and authentication are outside this local milestone.
A verified decision means it matches the exported evidence; no merge, deployment
or source update follows. No real human acceptance has been recorded here.

HTML/text/JSON payloads are escaped; artifact names are allowlisted; symlinks
escaping the evidence root are rejected. Outputs must be new directories outside
the source evidence run. The input is the retained trusted local testbed run,
not arbitrary remote source. Generated bindings and trusted evaluator test
migrations stay visible in the full review bundle.

Acceptance: tampered patches/manifests fail verification; stale revisions and
missing complete patches fail export; failed validation cannot be approved;
required reviewer fields are enforced; synthetic records are clearly separate
from real human acceptance; local browser checks demonstrate required fields,
failed approval gating and a downloaded synthetic rejection that verifies.
