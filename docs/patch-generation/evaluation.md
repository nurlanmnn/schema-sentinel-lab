# First local evaluation — 23 October 2026

SS-70's contract and fixture are implemented. SS-71's local endpoint completed
a representative request. SS-72's first-attempt model proposal failed safely;
there is no successful model-generated migration in this evaluation.

Hardware: MacBook Pro Mac16,1, Apple M4 (10 CPU cores), 16 GiB unified memory.
The only preinstalled model was Qwen 3.5 9B and was excluded by the model-origin
requirement. SS-15 was marked Done, but no visible description or comments
established a usable GPU or API resource. No sponsor compute or paid service was
used.

Devstral Small 2 24B was considered but not downloaded. Its listed 15 GB artifact
would leave inadequate practical headroom on this 16 GiB shared-memory machine
for the OS, inference context and active development tools. This is a capacity
assessment, not a measured out-of-memory test. The smaller candidate is
Mistral AI's Ministral 3 3B Instruct 2512, served as `ministral-3:3b`.
Mistral AI is the French model developer. The model is Apache 2.0; the Ollama
serving tool is MIT. Both permit an open-source path with their license notices
retained on redistribution. This is a local evaluation choice, not a team-wide
architecture adoption.

Primary references:

- https://ollama.com/library/devstral-small-2
- https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512
- https://ollama.com/library/ministral-3:3b
- https://github.com/ollama/ollama/blob/v0.30.8/LICENSE
- https://mistral.ai/about

| Recorded setting | Value |
| --- | --- |
| Model digest | f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d |
| Format / quantization | GGUF / Q4_K_M |
| Model metadata size | 3.8B parameters, 2,953,840,808 artifact bytes |
| Serving version | Ollama 0.30.8 |
| Configured request context / output limit | 16,384 / 8,192 tokens |
| Temperature / seed | 0 / 42 |
| Prompt version | 1.0; exact hash and messages saved |
| Source revision | 26304c1ed2f4738676a9607e8fe21e17ebd090f0 |
| Download request elapsed | 163.074 seconds; separate from inference |
| Local request elapsed | 33.228 seconds |
| Server total / load | 33.209 / 5.342 seconds |
| Prompt evaluation / generation | 15.618 / 12.156 seconds |
| Prompt / generated token counts | 5,488 / 315 |
| Maximum sampled model allocation | 4,029,960,682 bytes (about 3.75 GiB) |

The memory number is Ollama `/api/ps` allocation sampled once per second, not
whole-system peak RSS or a guaranteed maximum. Installation and downloads are
excluded from request elapsed time. These are local observations for one prepared
case, not project propagation performance, human baseline or human review time.

The endpoint returned JSON with rationale, confidence 0.98 and assumptions.
Its diff omitted required git headers and was rejected before an application
worktree was created. It proposed only a schema fragment, missed the Python,
TypeScript and C# construction/read changes, and incorrectly assumed regenerated
bindings would suffice. Its reservation explanation was imprecise: reserved
fields prevent reuse; they are not decoded into a new application-visible slot.
The high self-reported confidence did not predict correctness. The model fits
this hardware and accepts the context; its first response is not useful enough
to accept. No response was repaired and no second model was downloaded.

Raw evidence is under `patchgen/evidence/live-001/`: request, prompt, complete
model/license metadata, raw response, parsed proposal, sampled allocation and
failure report. `model-setup/` records hardware and the separately timed download.

An independent reference patch was checked separately using `--response`.
`patchgen/evidence/offline-reference/report.json` is explicitly `offline_replay`
and reports `validation_passed`. Its log records configured Buf regeneration,
Python dependency setup, TypeScript and .NET builds, all 11 existing unit tests,
all four original round-trip cases, and five independent oracle cases including
a legacy field-2 payload. All three decoded-observation maps contained only
`entity_id`; service order and identifier values survived. `validated.patch`
includes generated changes from the configured plugins. This establishes that
the reference fixture and validation harness work. It does not establish model
patch success or mixed-version compatibility.

The contract/rejection suite also passes. Follow-up work is to improve structured
patch production while preserving this failed first attempt, obtain a successful
live proposal, and review the detector/locator interface questions in contract.md.
No detector integration, benchmark claims, automatic repair or merge is included.

A subsequent standalone oracle check exposed a readiness race: checking only the
Python health endpoint could send a request before a downstream service was ready
(HTTP 502/400). That failure remains in `offline-reference/oracle-cleanup-check.log`.
The oracle now waits for C#, TypeScript and Python health and interrupts the
runner gracefully for cleanup. `oracle-readiness-check.log` records all five
cases passing after the fix. No listeners remained on ports 8000–8002 afterward.
The original live model failure and original offline validation record are intact.
