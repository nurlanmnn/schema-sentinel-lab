# DeepSeek trial: provider unavailable

The user explicitly authorized this bounded Qwen/DeepSeek test exception.
Selected `deepseek-ai/deepseek-v4.1-flash` through NVIDIA's direct hosted endpoint.
The project default model selection and human-review gate remain unchanged.

**No model-quality result is available. Zero benchmark cases were attempted and
zero patches were generated. This is not a 0/8 patch-validation result.**

- First connectivity request: 4096 output-token cap; NVIDIA returned HTTP 504
  after about 300 seconds. No model response was received.
- One smaller connectivity attempt: 64 output-token cap and explicit 90-second
  socket timeout. It timed out after 90.14 seconds. No model response was received.
- The eight-case benchmark was not started because connectivity was unavailable.
  No repair, fallback, paid request, or local model download occurred.

The frozen intended trial was the same eight public synthetic cases and semantic
block prompt 3.1 used with Gemma and Laguna. The shared 4096-token output cap is
far below the larger default/recommended budget documented for this DeepSeek
model, so a future completed trial would measure that bounded configuration.

NVIDIA's Qwen3-Coder-480B endpoint is marked deprecated. The OpenRouter public
catalog check found no Qwen/DeepSeek model with both zero prompt and completion
prices; no paid alternative was invoked. Provider discovery is a time-specific
snapshot, not a claim of permanent unavailability.

All 270 patch-generation tests pass, including synthetic HTTP serialization of
the explicitly selected DeepSeek identifier with no Nemotron-only flags. These
implementation tests do not establish real serving availability or model quality.
Raw request bodies, the first provider error and both timing records are kept
in the two sibling connectivity evidence directories. Credentials were not saved.

The bounded test attempt is closed due to provider failure. A later retry must
use a fresh evidence directory; no background run or automatic retry is pending.
