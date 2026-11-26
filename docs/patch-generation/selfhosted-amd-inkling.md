# Screening Inkling 2 Mini on an AMD Developer Cloud GPU

This is a screening run on the 8 development cases. It is not the held-out evaluation.

## Why llama.cpp and not vLLM

The official Inkling 2 Mini weights (`thinkingmachines/Inkling-2-Mini`, 19.5 GB) store the experts in NVIDIA FP4 (`nvfp4`). The MI300X has no FP4 hardware, so vLLM on ROCm is unlikely to serve them as published.

ggml-org publishes GGUF conversions that llama.cpp runs on ROCm:

| File | Size | Use |
|---|---|---|
| `Inkling-2-Mini-Q8_0.gguf` | 27.8 GB | Primary. This fits the sponsor's one-workstation-GPU path (32 GB card). |
| `Inkling-2-Mini-BF16.gguf` | 52.2 GB | Optional. Full precision, to check how much the 8-bit version loses. |

## Costs and safety

- One MI300X droplet costs about $2 an hour (check the console price). The $100 credit expires on 2026-12-02.
- **A powered-off droplet is still billed. Destroy it when finished.**
- The server listens only on the droplet's loopback address. The Mac reaches it through an SSH tunnel, so nothing is exposed to the internet and no API key is used.

## 1. Create the droplet (account owner)

1. Go to the AMD Developer Cloud console and choose **Create → GPU Droplet**.
2. Pick **1× MI300X** and the **ROCm** software image (Ubuntu with ROCm and Docker).
3. Under SSH keys, select `schema-sentinel-amd` (the public half of `~/.ssh/schema_sentinel_amd`, which has no passphrase). The web console may not work on newer images, so the key must be chosen at creation.
4. Create the droplet and copy its public IP address.

## 2. Start the server (on the droplet)

```bash
ssh root@<IP>
mkdir -p ~/models
curl -fL -o ~/models/Inkling-2-Mini-Q8_0.gguf \
  https://huggingface.co/ggml-org/Inkling-2-Mini-GGUF/resolve/main/Inkling-2-Mini-Q8_0.gguf
sha256sum ~/models/Inkling-2-Mini-Q8_0.gguf   # must be d57542f8aea5d7639beba5fc4ae7f584754916f63ac5d5a69328c27f652f45da
docker run -d --name inkling --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt seccomp=unconfined -v ~/models:/models -p 127.0.0.1:8080:8080 \
  ghcr.io/ggml-org/llama.cpp:server-rocm-b12723 \
  -m /models/Inkling-2-Mini-Q8_0.gguf --alias inkling-2-mini-q8_0 \
  --host 0.0.0.0 --port 8080 -ngl 999 -c 131072 --jinja
docker logs -f inkling
```

The context is shared by llama.cpp's 4 parallel slots, so 131072 gives each concurrent request 32768 tokens. With `-c 32768`, concurrent requests fail with "context size has been exceeded".

Record the `sha256sum` output and the llama.cpp build line from the log with the evidence.

## 3. Tunnel and run (on the Mac)

```bash
ssh -N -L 8080:127.0.0.1:8080 root@<IP>
```

In a second terminal, in this repository:

```bash
.venv/bin/python -m patchgen.live_suite --output patchgen/evidence/dev-inkling-q8 \
  --backend selfhosted --model inkling-2-mini-q8_0 --strategy candidate_semantic_blocks \
  --case pubsub-rename --case pubsub-removal --case pubsub-utf8 --case telemetry-rename \
  --case telemetry-precision --case telemetry-units --case inventory-width --case telemetry-quantized
```

Run one case first. llama.cpp must return the model's reasoning in `reasoning_content` and only the JSON answer in `content`. If the reasoning shows up in `content`, the chat-template reasoning parser isn't active; fix that before running the rest.

## 4. Destroy the droplet

Destroy it in the console. Powering it off is not enough.
