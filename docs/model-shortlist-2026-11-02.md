# Local model reassessment — November 2, 2026

The installed Ministral 3 8B produced no validated proposal on either six-case
one-shot trial. A better edit format increased contract passes without fixing
the migrations. This supports testing a different model configuration; it does
not establish that every small local model will fail.

The prepared host has 16 GiB unified memory, about 85 GiB free disk space at this
checkpoint, and Ollama 0.30.8. The 8B model used about 7.4 GB of Ollama model
allocation at 16K context. These observations are not peak-memory guarantees.

| Candidate | Local package | Why investigate | Current evidence / boundary |
| --- | --- | --- | --- |
| Installed Ministral 3 3B | Already installed | A no-download size comparison using the frozen 2.5 protocol | Completed 0/6; 11/18 file contracts; faster/smaller than 8B on this host, no validated migration |
| Ministral 3 14B | Official Q4_K_M, about 9.1 GB; digest prefix `4760c35aeb9d` | Controlled same-family size comparison before changing the prompt | User approved November 2; installed and six-case comparison started; no result yet |
| Gemma 4 12B | Official `gemma4:12b-it-q4_K_M`, 8.0 GB; digest prefix `6114515d63c1` | A different model family with a smaller package than the 14B candidate | Not installed or authorized for download; serving compatibility, memory and migration quality unmeasured |

[Mistral's model documentation](https://docs.mistral.ai/models/ministral-3-14b-25-12)
identifies the 14B model and Apache-2.0 license. Package properties come from the
[official Ollama tag](https://ollama.com/library/ministral-3:14b).

[Google's Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
identifies Google DeepMind as the author, Apache-2.0 licensing, and coding and
reasoning as supported uses. The exact quantization and package size above come
from the [official Ollama tag](https://ollama.com/library/gemma4:12b-it-q4_K_M).
Google's [memory guidance](https://ai.google.dev/gemma/docs/core) separates static
weights from context-cache requirements. A smaller download is not proof of a
smaller total working set or better patches on this Mac.

Devstral Small 2 is designed for software engineering, but its dense 24B size is
a less practical first experiment here. Mistral's [local deployment guidance](https://docs.mistral.ai/vibe/code/cli/offline-models)
recommends a 24 GB GPU for its 4-bit, 32K-context configuration and notes that CPU
offload is slower. This does not prove that all smaller-context deployments are
impossible; it explains why it is not the first candidate for the 16 GiB host.

Use the same six inputs, prompt 2.5, options and captured gates for the first
controlled model comparison. Exact digests and actual request payloads matter;
the same prompt-version label alone is insufficient. A model's recommended
sampling/thinking settings may differ from the frozen settings. Evaluate such
model-specific tuning as a separate protocol rather than silently changing it.

Vendor benchmark claims are not Schema Sentinel validation evidence. The user
explicitly authorized the 14B download and local comparison on November 2.
No paid endpoint is used and no capability or memory fit is claimed from this
shortlist. The user's non-Chinese-model constraint remains
in effect; Qwen is excluded from these experiments.

The CLI is prepared for the 14B tag and requires it to be installed locally.
Missing weights stop at the tag preflight; there is no automatic pull or remote
fallback. The authorized installation retained full digest
`4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7`.
Installation and pre-run host evidence are in
`patchgen/evidence/ministral14b-install001/`. The frozen comparison command is:

```sh
.venv/bin/python -m patchgen.live_suite --model ministral-3:14b --output patchgen/evidence/NEW-live-14b
```

This command uses the frozen prompt 2.5 by default. The same comparison audit can
compare the completed result against the retained 8B baseline. Gemma remains a
researched alternative, with no integration or serving compatibility claim.
