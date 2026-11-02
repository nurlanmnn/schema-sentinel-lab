# Decision 0011: retain review evidence for blocked analysis

Date: 2 November 2026
Status: independent implementation; real human review pending

When detector/locator/adapter records cannot pass the adapter gate, save a
structured rejected pipeline report with the blocking stage, reason and explicit
generation/validation `not_run` values. Preserve a minimal request containing
schema identity, source revision and intended behavior, excluding caller-supplied
candidate positions. Do not create adapted generator input or a proposal.

The portable review exporter can display this rejected report without a proposal.
Its manifest explicitly selects the allowlisted request/report artifact names.
Only a proposal report with passing validation and a complete patch can enable
approval. Blocked-analysis reviews permit rejection only. Verification checks
selected artifact identities and hashes; existing manifests default to the older
input/proposal-report names. The static assets and decision format are unchanged.

This closes the review-evidence gap at the analysis gate; it does not relax that
gate or turn rejection into successful migration. The report applies once schema
source identity has been verified and analysis records exist. Invalid requests,
missing source revisions or descriptor-build errors may still terminate earlier
with an error record. Self-reported decisions remain unauthenticated, and no
decision is created on a person's behalf or followed by code application/merge.

Acceptance: a semantic-only detector rejection retains its request/report and can
export a rejection-only review; a real pinned enum fixture is blocked at locator
and exports evidence without inference; missing proposal reports cannot claim
passing validation; existing passing/failed proposal exports and integrity tests
continue to pass. Synthetic test decisions never represent real acceptance.
