# Decision 0040: explicit DeepSeek comparison trial

The user explicitly requested testing Qwen or DeepSeek after previously excluding
Chinese-developed models. Treat this as a bounded trial exception, not a sponsor
approval or a change to the project's default model selection. Use only the
existing public synthetic benchmark through NVIDIA's direct hosted API. Do not
enable fallback, download local weights, or transmit controlled material.

NVIDIA's current Qwen Coder endpoint is marked deprecated. Select the active
`deepseek-ai/deepseek-v4.1-flash` endpoint instead, subject to a successful
connectivity/identity probe:
https://build.nvidia.com/deepseek-ai/deepseek-v4.1-flash
https://build.nvidia.com/qwen/qwen3-coder-480b-a35b-instruct/deploy

Freeze `candidate_semantic_blocks` prompt 3.1, the same eight source revisions,
JSON-envelope parser, edit contracts, compilation/unit checks and independent
runtime oracles. Use one sample per case, no model repair or automatic retry.
Retain failures. Human approval remains required; no generated patch is merged.

Use the documented sampling defaults temperature 1/top_p .95 with the same 4096
output-token budget used for Ultra, Gemma and Laguna. Do not send Nemotron-only
chat-template flags or guess an undocumented reasoning switch. NVIDIA's reference
API defaults to 262144 max_tokens, and the model card recommends a much larger
output budget. This deliberately small-budget comparison therefore measures the
selected configuration, not the model's maximum achievable capability. Record
truncation explicitly if it occurs. Provider-default reasoning behavior is not
held constant across different model families.

https://docs.api.nvidia.com/nim/reference/nvidia-deepseek-v4_1-flash-infer

This is an authored development benchmark, not unseen-case generalization or a
full twenty-case live-model result. Evidence lives in
`patchgen/evidence/nvidia-deepseek-v41-flash-001`.

## Outcome: serving unavailable, no quality score

The initial connectivity request returned NVIDIA HTTP 504 after approximately
300 seconds. One smaller 64-token connectivity attempt, with an explicit
90-second socket timeout, also timed out. No benchmark case was attempted and
no patch was generated. Record provider_unavailable and a null quality rate,
not 0/8. The current OpenRouter public catalog contained no Qwen/DeepSeek model
with zero prompt and completion prices; no paid alternative was invoked.
All 270 implementation tests passed. The bounded trial attempt is closed, with
no automatic retry pending. Default model selection remains unchanged.
