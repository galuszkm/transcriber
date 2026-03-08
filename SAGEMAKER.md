# Deploying the Transcription Service on AWS SageMaker

This document describes how to deploy the **transcriber** inference server on
[AWS SageMaker](https://aws.amazon.com/sagemaker/) as a real-time endpoint
using the **Bring Your Own Container (BYOC)** approach.

---

## Table of Contents

1. [SageMaker Container Contract](#sagemaker-container-contract)
2. [Readiness Assessment](#readiness-assessment)
3. [What Was Added](#what-was-added)
4. [Building the Docker Image](#building-the-docker-image)
5. [Deploying to SageMaker](#deploying-to-sagemaker)
6. [Endpoint Usage](#endpoint-usage)
7. [Limitations & Differences from Local](#limitations--differences-from-local)
8. [References](#references)

---

## SageMaker Container Contract

AWS SageMaker requires custom inference containers to satisfy a specific HTTP
API contract.  The requirements below are sourced from official AWS
documentation and the
[`aws/sagemaker-inference-toolkit`](https://github.com/aws/sagemaker-inference-toolkit)
reference implementation.

| Requirement | Detail | Source |
|---|---|---|
| **Port** | Container must listen on **port 8080** (the official SageMaker toolkit uses `SAGEMAKER_BIND_TO_PORT` env var; this project uses `SAGEMAKER_PORT` for the same purpose). | [`aws/amazon-sagemaker-examples` — `main.py`](https://github.com/aws/amazon-sagemaker-examples/blob/default/archived/inference_pipeline_custom_containers/containers/postprocessor/docker/code/main.py) |
| **`GET /ping`** | Health-check endpoint.  Must return **HTTP 200** when healthy (model loaded). SageMaker calls this periodically. | [`aws/amazon-sagemaker-examples` — `preprocessing.py`](https://github.com/aws/amazon-sagemaker-examples/blob/default/archived/byoc-nginx-python/featurizer/code/preprocessing.py) |
| **`POST /invocations`** | Inference endpoint.  Receives audio payload, returns prediction JSON.  Must respond within **60 seconds** for standard real-time endpoints.  Max payload **25 MB**. | [SageMaker Inference Toolkit — `parameters.py`](https://github.com/aws/sagemaker-pytorch-inference-toolkit/blob/master/src/sagemaker_inference/parameters.py) |
| **Model artifacts** | SageMaker unpacks `model.tar.gz` from S3 into `/opt/ml/model` at container startup.  The container must be able to load models from this path. | [AWS docs: *Use Your Own Inference Code*](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html) |
| **`serve` argument** | SageMaker invokes the container with `serve` as the first CLI argument (i.e. `docker run <image> serve`). | [AWS example — `main.py` entrypoint check](https://github.com/aws/amazon-sagemaker-examples/blob/default/archived/inference_pipeline_custom_containers/containers/postprocessor/docker/code/main.py) |
| **Logging** | All logs to `stdout`/`stderr` for CloudWatch collection. | General SageMaker guidance |

---

## Readiness Assessment

### ✅ Already Satisfied (Before Changes)

| Requirement | How the Service Already Met It |
|---|---|
| FastAPI HTTP server | The service already uses FastAPI + Uvicorn as its serving stack. |
| Health check | `GET /health` exists and returns model readiness status. |
| Multiple input formats | The server accepts multipart file uploads, base64 JSON, and raw bytes — all usable via `/invocations`. |
| Streaming support | SSE endpoints (`/transcribe/stream`) emit chunked responses compatible with SageMaker's `InvokeEndpointWithResponseStream` API. |
| Environment-based config | All config (model size, device, HF token, etc.) is read from env vars via `pydantic-settings`. |
| Logging to stdout | Uvicorn and Python `logging` write to stdout/stderr by default. |

### ❌ Gaps Identified (Now Resolved)

| Gap | Resolution |
|---|---|
| No `GET /ping` endpoint | **Added** — returns HTTP 200 when model loaded, 503 otherwise. |
| No `POST /invocations` endpoint | **Added** — content-type-aware endpoint supporting `application/json`, `application/octet-stream`, and `multipart/form-data`. |
| Default port was 8000, not 8080 | **Added** — `SAGEMAKER_PORT` env var support; defaults to 8000 for local dev, set to 8080 in the Dockerfile for SageMaker. |
| No Dockerfile | **Added** — GPU-ready Dockerfile based on `nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04`. |
| No `serve` entrypoint | **Added** — `docker/entrypoint.sh` handles the `serve` argument SageMaker passes. |
| Host bound to `127.0.0.1` by default | **Added** — `SAGEMAKER_BIND` env var support; set to `0.0.0.0` in the Dockerfile. |

### ⚠️ Limitations (Cannot Be Resolved)

| Limitation | Detail |
|---|---|
| **WebSocket not supported** | SageMaker real-time endpoints only support HTTP POST/GET.  The `/ws/transcribe` WebSocket endpoint **will not work** on SageMaker.  Use the HTTP endpoints instead. ([Source](https://github.com/aws/sagemaker-inference-toolkit)) |
| **60-second inference timeout** | Standard SageMaker real-time endpoints timeout after 60 seconds ([source](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html)).  Long audio files may exceed this.  Mitigations: use **Asynchronous Inference** (up to 1 hour timeout), or select a faster model size (`small` instead of `large-v3`). ([Async Inference docs](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)) |
| **25 MB payload limit** | Audio files larger than 25 MB must be pre-uploaded to S3 and passed as a reference, or use SageMaker Asynchronous Inference (up to 1 GB). |
| **No SSE via standard `/invocations`** | Streaming progress via SSE requires the `InvokeEndpointWithResponseStream` API on the client side.  Standard `InvokeEndpoint` returns a single response. |

---

## What Was Added

### 1. SageMaker Endpoints (`src/transcriber/server/routes.py`)

Two new routes were added alongside all existing endpoints:

```
GET  /ping          → 200 (ready) or 503 (loading)
POST /invocations   → Transcription result (JSON)
```

`/invocations` automatically detects the input format from `Content-Type`:

| Content-Type | Input Format |
|---|---|
| `application/json` | JSON body with `audio_base64` field |
| `application/octet-stream` | Raw audio bytes |
| `multipart/form-data` | File upload in `file` field |
| *(other / missing)* | Treated as raw bytes |

### 2. SageMaker-Aware Configuration (`src/transcriber/server/app.py`)

Environment variables for SageMaker deployment:

| Variable | Default | Purpose |
|---|---|---|
| `SAGEMAKER_PORT` | `8000` | Override the listening port (set to `8080` in Dockerfile) |
| `SAGEMAKER_BIND` | `127.0.0.1` | Override the bind address (set to `0.0.0.0` in Dockerfile) |

These do **not** affect local development — the defaults remain `127.0.0.1:8000`.

### 3. Dockerfile

A multi-stage Dockerfile at the repository root:

- **Base**: `nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04`
- **Python deps**: Installed via `uv` with the `server` extra (includes `ml`)
- **Port**: Exposes 8080
- **Entrypoint**: `docker/entrypoint.sh` handles the `serve` argument

### 4. Entrypoint Script (`docker/entrypoint.sh`)

A shell script that starts `trans-server` with configuration from environment
variables.  SageMaker passes `serve` as `$1` — the script ignores the argument
and starts the server.

---

## Building the Docker Image

```bash
# Build the image
docker build -t transcriber-inference .

# Run locally (GPU)
docker run --gpus all -p 8080:8080 transcriber-inference

# Run locally (CPU)
docker run -p 8080:8080 -e DEVICE=cpu transcriber-inference

# Test health
curl http://localhost:8080/ping

# Test inference
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/octet-stream" \
  --data-binary @audio.wav
```

---

## Deploying to SageMaker

### Prerequisites

- AWS CLI configured
- Amazon ECR repository created
- IAM role with SageMaker execution permissions

### Step 1: Push Image to ECR

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REPO=transcriber-inference

# Authenticate
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag and push
docker tag transcriber-inference:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
```

### Step 2: Create SageMaker Model

```python
import boto3

sm = boto3.client("sagemaker")
account_id = boto3.client("sts").get_caller_identity()["Account"]
region = "us-east-1"

sm.create_model(
    ModelName="transcriber-model",
    PrimaryContainer={
        "Image": f"{account_id}.dkr.ecr.{region}.amazonaws.com/transcriber-inference:latest",
        # ModelDataUrl is optional — the container downloads models from
        # HuggingFace on startup.  To use pre-cached models, upload a
        # model.tar.gz to S3 and set ModelDataUrl here.
        "Environment": {
            "MODEL": "large-v3",
            "DEVICE": "cuda",
            "HF_TOKEN": "hf_...",  # Required for diarization only
        },
    },
    ExecutionRoleArn=f"arn:aws:iam::{account_id}:role/SageMakerExecutionRole",
)
```

### Step 3: Create Endpoint Configuration

```python
sm.create_endpoint_config(
    EndpointConfigName="transcriber-config",
    ProductionVariants=[
        {
            "VariantName": "primary",
            "ModelName": "transcriber-model",
            "InstanceType": "ml.g5.xlarge",   # NVIDIA A10G GPU
            "InitialInstanceCount": 1,
            "ContainerStartupHealthCheckTimeoutInSeconds": 600,  # Model loading takes time
        },
    ],
)
```

### Step 4: Deploy Endpoint

```python
sm.create_endpoint(
    EndpointName="transcriber-endpoint",
    EndpointConfigName="transcriber-config",
)

# Wait for deployment (may take 5–10 minutes for model download)
waiter = sm.get_waiter("endpoint_in_service")
waiter.wait(EndpointName="transcriber-endpoint")
```

### Step 5: Invoke

```python
import json

runtime = boto3.client("sagemaker-runtime")

# With raw audio bytes
with open("audio.wav", "rb") as f:
    response = runtime.invoke_endpoint(
        EndpointName="transcriber-endpoint",
        ContentType="application/octet-stream",
        Body=f.read(),
    )

result = json.loads(response["Body"].read())
print(result["transcript"])

# With base64 JSON
import base64

with open("audio.wav", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

response = runtime.invoke_endpoint(
    EndpointName="transcriber-endpoint",
    ContentType="application/json",
    Body=json.dumps({"audio_base64": audio_b64, "diarize": False}),
)

result = json.loads(response["Body"].read())
print(result["transcript"])
```

---

## Endpoint Usage

### Local Endpoints (Still Available)

All existing endpoints continue to work as before:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Detailed health (model size, device, queue) |
| `/transcribe` | POST | Multipart or base64 form |
| `/transcribe/json` | POST | JSON body with base64 |
| `/transcribe/raw` | POST | Raw audio bytes |
| `/transcribe/stream` | POST | SSE streaming |
| `/transcribe/json/stream` | POST | SSE streaming (JSON input) |
| `/transcribe/raw/stream` | POST | SSE streaming (raw input) |
| `/ws/transcribe` | WebSocket | Continuous transcription |

### SageMaker Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/ping` | GET | SageMaker health check (200/503) |
| `/invocations` | POST | SageMaker inference (auto-detects content type) |

---

## Limitations & Differences from Local

| Feature | Local | SageMaker |
|---|---|---|
| WebSocket (`/ws/transcribe`) | ✅ Works | ❌ Not supported (HTTP only) |
| SSE streaming | ✅ Works | ⚠️ Requires `InvokeEndpointWithResponseStream` API |
| Inference timeout | Unlimited | 60 sec (standard) / 1 hour (async) |
| Max payload | Unlimited | 25 MB (standard) / 1 GB (async) |
| Port | 8000 | 8080 (SageMaker contract) |
| Bind address | 127.0.0.1 | 0.0.0.0 (container requirement) |
| Model loading | HuggingFace download | HuggingFace download or `/opt/ml/model` |

### Asynchronous Inference (Recommended for Long Audio)

For audio files that may take longer than 60 seconds to transcribe, use
[SageMaker Asynchronous Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html):

- Up to **1 hour** processing time
- Up to **1 GB** payload size
- Input/output via S3
- SNS notifications on completion
- Auto-scales to zero when idle

The same container image works for both real-time and asynchronous endpoints —
SageMaker handles the S3 I/O and timeout management automatically.

---

## References

- [AWS SageMaker: Use Your Own Inference Code](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html)
- [AWS SageMaker: Adapt Your Own Inference Container](https://docs.aws.amazon.com/sagemaker/latest/dg/adapt-inference-container.html)
- [AWS SageMaker Inference Toolkit (GitHub)](https://github.com/aws/sagemaker-inference-toolkit)
- [AWS SageMaker Examples — BYOC](https://github.com/aws/amazon-sagemaker-examples)
- [SageMaker Inference Toolkit — `parameters.py`](https://github.com/aws/sagemaker-pytorch-inference-toolkit/blob/master/src/sagemaker_inference/parameters.py) — defines `SAGEMAKER_BIND_TO_PORT`, `SAGEMAKER_MODEL_SERVER_TIMEOUT`, etc.
- [AWS SageMaker Streaming Inference Blog](https://aws.amazon.com/blogs/machine-learning/elevating-the-generative-ai-experience-introducing-streaming-support-in-amazon-sagemaker-hosting/)
- [AWS SageMaker Asynchronous Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)
