# Decision 0004: independent descriptor pipeline and candidate review

Date: 1 November 2026
Status: independent implementation; human review pending

Work lives in the self-contained Lab checkout and personal private repository.
Inherited source/history and earlier experiments remain attributed and intact.
The team upstream push URL remains disabled. This does not replace or merge a
teammate branch, settle team ownership, or establish team acceptance.

Build both old and new descriptors from the same canonical relative path and
package. Compare messages by fully qualified name and fields by wire number.
Never infer structured semantics from Buf diagnostic prose. This slice exports
one field removal, rename, type change, or enum-value addition per request.
Multiple events, unsupported changes, missing intended behavior, or identity
changes produce partial records. Caller-supplied intended behavior is required;
units, coordinate frames and meaning are not inferred from comments.

Use supported language-specific Tree-sitter wheels rather than the old grammar
bundle. Scan tracked runtime Python/TypeScript/C# sources at the exact commit.
Include identifier/property uses, keyword/object construction, cast-based member
reads, snake/camel/Pascal naming, and selected literal-key/reflection forms.
Do not filter by a guessed receiver type: conservative candidates include other
versions or unrelated types. This favors recall in the measured fixture. The
record's complete status means the bounded static scan completed without a known
parser/explicit dynamic-access error, never whole-program impact completeness.
Generated bindings and test files are outside this runtime scan. Enum consumer
analysis is unsupported and yields partial output; it cannot flow to generation.

Prompt 2.5 is a separately measured strategy. Each candidate line needs an
edit/unaffected decision and nonempty reason. Edit candidates must be covered;
unaffected lines cannot be covered by an edit. The host checks these mechanical
conditions but cannot verify a model's semantic justification. Independent
compilation and runtime oracles remain necessary. Earlier prompts and failed
responses remain unchanged. The prompt also explicitly requests preserved
indentation and TypeScript encoder/decoder instances in response to the recorded
2.4 failures. This is an informed follow-up experiment, not a blind model test
or hidden repair of earlier responses. There is still one request per runtime,
no repair loop and no automatic acceptance or merge.

Third-party licenses shipped in the adopted wheels are copied under
`docs/licenses/pipeline/`: the four Tree-sitter packages use MIT; protobuf uses
BSD-3-Clause. The pinned environment is separate from evaluated runtime manifests.
These permissive dependencies do not require making this private repository
public. Existing repository-wide licensing and inherited dependencies remain
separate from this narrow dependency review.

Acceptance gates: structural classifications match independent field-change
expectations; exact committed snapshots/hashes are retained; every reference
runtime site is found; conservative extras are reported; parser/unsupported
outcomes fail closed; output passes the existing adapter; every live attempt is
retained; validation and human review remain separate gates. A twenty-case
realistic benchmark, active enum handling, semantic/type resolution, manual time
baseline, pub/sub demo and review interface are later milestones.
