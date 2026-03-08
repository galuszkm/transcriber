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
7. [Bypassing Timeout & Payload Limits](#bypassing-timeout--payload-limits)
8. [Limitations & Differences from Local](#limitations--differences-from-local)
9. [References](#references)

---

## SageMaker Container Contract

AWS SageMaker requires custom inference containers to satisfy a specific HTTP
API contract.  The requirements below are sourced from official AWS
documentation and the
[`aws/sagemaker-inference-toolkit`](https://github.com/aws/sagemaker-inference-toolkit)
reference implementation.

| Requirement | Detail | Source |
|---|---|---|
| **Port** | Container must listen on **port 8080**. | [`aws/amazon-sagemaker-examples` — `main.py`](https://github.com/aws/amazon-sagemaker-examples/blob/default/archived/inference_pipeline_custom_containers/containers/postprocessor/docker/code/main.py) |
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
| Multiple input formats | The server accepts multipart file uploads, base64 JSON, and raw bytes — all usable via `/invocations`. |
| Streaming support | SSE endpoints (`/transcribe/stream`) emit chunked responses compatible with SageMaker's `InvokeEndpointWithResponseStream` API. |
| Environment-based config | All config (model size, device, HF token, etc.) is read from env vars via `pydantic-settings`. |
| Logging to stdout | Uvicorn and Python `logging` write to stdout/stderr by default. |

### ❌ Gaps Identified (Now Resolved)

| Gap | Resolution |
|---|---|
| No `GET /ping` endpoint | **Added** — returns HTTP 200 with `HealthResponse` when model loaded, HTTP 503 otherwise.  Shares the same handler as `/health`. |
| No `POST /invocations` endpoint | **Added** — content-type-aware endpoint supporting `application/json`, `application/octet-stream`, and `multipart/form-data`.  Uses the shared `_submit_transcription()` helper. |
| Default port was 8000, not 8080 | **Changed** — default port is now **8080** and default host is **0.0.0.0**, matching the SageMaker contract out of the box. |
| No Dockerfile | **Added** — GPU-ready Dockerfile based on `nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04`. |
| No `serve` entrypoint | **Added** — `docker/entrypoint.sh` handles the `serve` argument SageMaker passes. |

---

## What Was Added

### 1. SageMaker Endpoints (`src/transcriber/server/routes.py`)

Two new routes alongside all existing endpoints:

```
GET  /ping          → 200 + HealthResponse (ready) or 503 + HealthResponse (loading)
POST /invocations   → Transcription result (JSON)
```

`/ping` and `/health` share the same handler function (`_health_response`).
Both return the full `HealthResponse` body and use HTTP status codes to
indicate readiness (200 = ready, 503 = loading).

`/invocations` automatically detects the input format from `Content-Type`:

| Content-Type | Input Format |
|---|---|
| `application/json` | JSON body with `audio_base64` field |
| `application/octet-stream` | Raw audio bytes |
| `multipart/form-data` | File upload in `file` field |
| *(other / missing)* | Treated as raw bytes |

All transcription endpoints (`/invocations`, `/transcribe`, `/transcribe/json`,
`/transcribe/raw`) use the shared `_submit_transcription()` helper to avoid
code duplication.

### 2. Default Port & Host (`src/transcriber/server/app.py`)

The server now defaults to **`0.0.0.0:8080`** — the SageMaker-required address.
No extra environment variables are needed; `--host` and `--port` CLI arguments
can still override the defaults.

### 3. Dockerfile

A Dockerfile at the repository root:

- **Base**: `nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04`
- **Python deps**: Installed via `uv` with the `server` extra (includes `ml`)
- **Port**: Exposes 8080
- **Entrypoint**: `docker/entrypoint.sh` handles the `serve` argument

### 4. Entrypoint Script (`docker/entrypoint.sh`)

A shell script that starts `trans-server` with model configuration from
environment variables.  SageMaker passes `serve` as `$1` — the script ignores
the argument and starts the server on the default `0.0.0.0:8080`.

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

For **real-time** inference (≤ 60 s processing, ≤ 25 MB payload):

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

For **asynchronous** inference (≤ 1 hour processing, ≤ 1 GB payload) — see
[Bypassing Timeout & Payload Limits](#bypassing-timeout--payload-limits) below.

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

All endpoints are available both locally and on SageMaker:

| Endpoint | Method | Description |
|---|---|---|
| `/ping` | GET | Health check — 200 (ready) / 503 (loading) with `HealthResponse` body |
| `/health` | GET | Same handler as `/ping` — identical response |
| `/invocations` | POST | SageMaker inference — auto-detects content type |
| `/transcribe` | POST | Multipart or base64 form |
| `/transcribe/json` | POST | JSON body with base64 |
| `/transcribe/raw` | POST | Raw audio bytes |
| `/transcribe/stream` | POST | SSE streaming |
| `/transcribe/json/stream` | POST | SSE streaming (JSON input) |
| `/transcribe/raw/stream` | POST | SSE streaming (raw input) |
| `/ws/transcribe` | WebSocket | Continuous transcription |

---

## Bypassing Timeout & Payload Limits

SageMaker real-time endpoints have a **60-second inference timeout** and
**25 MB maximum payload** — these limits are hardcoded and
[cannot be increased](https://github.com/aws/sagemaker-python-sdk/issues/1119).
For audio files that exceed these limits, SageMaker offers two alternatives
that work with the **exact same container image** — no code changes required.

### Asynchronous Inference (Recommended)

[SageMaker Async Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)
completely bypasses both limits:

| Limit | Real-Time | Async |
|---|---|---|
| Inference timeout | 60 seconds | **up to 1 hour** |
| Max payload | 25 MB | **up to 1 GB** |
| Scaling to zero | ❌ | ✅ (cost savings when idle) |

The container's `/invocations` endpoint is called identically — SageMaker
handles S3 upload/download and timeout management automatically.

#### Deploying an Async Endpoint

```python
sm.create_endpoint_config(
    EndpointConfigName="transcriber-async-config",
    ProductionVariants=[
        {
            "VariantName": "primary",
            "ModelName": "transcriber-model",
            "InstanceType": "ml.g5.xlarge",
            "InitialInstanceCount": 1,
            "ContainerStartupHealthCheckTimeoutInSeconds": 600,
        },
    ],
    AsyncInferenceConfig={
        "OutputConfig": {
            "S3OutputPath": "s3://my-bucket/transcriber-output/",
            # Optional: get notified when transcription completes
            # "NotificationConfig": {
            #     "SuccessTopic": "arn:aws:sns:us-east-1:123456789:TranscribeSuccess",
            #     "ErrorTopic": "arn:aws:sns:us-east-1:123456789:TranscribeError",
            # },
        },
        "ClientConfig": {
            "MaxConcurrentInvocationsPerInstance": 1,  # GPU constraint
        },
    },
)

sm.create_endpoint(
    EndpointName="transcriber-async-endpoint",
    EndpointConfigName="transcriber-async-config",
)
```

#### Invoking an Async Endpoint

```python
import boto3

runtime = boto3.client("sagemaker-runtime")

# 1. Upload audio to S3
s3 = boto3.client("s3")
s3.upload_file("long_meeting.wav", "my-bucket", "inputs/long_meeting.wav")

# 2. Invoke asynchronously
response = runtime.invoke_endpoint_async(
    EndpointName="transcriber-async-endpoint",
    InputLocation="s3://my-bucket/inputs/long_meeting.wav",
    ContentType="application/octet-stream",
    InvocationTimeoutSeconds=3600,  # up to 1 hour
)

# 3. Poll for result or use SNS notification
output_location = response["OutputLocation"]
print(f"Result will be at: {output_location}")
```

### Streaming Inference

For real-time progress feedback, the SSE streaming endpoints
(`/transcribe/stream`, `/transcribe/json/stream`, `/transcribe/raw/stream`)
work with SageMaker's
[`InvokeEndpointWithResponseStream`](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpointWithResponseStream.html)
API.  This extends the response timeout to **8 minutes** and delivers chunked
responses as they are generated.

---

## Limitations & Differences from Local

| Feature | Local | SageMaker Real-Time | SageMaker Async |
|---|---|---|---|
| WebSocket (`/ws/transcribe`) | ✅ Works | ❌ Not supported | ❌ Not supported |
| SSE streaming | ✅ Works | ⚠️ Via `InvokeEndpointWithResponseStream` | ❌ Not applicable |
| Inference timeout | Unlimited | 60 sec | **1 hour** |
| Max payload | Unlimited | 25 MB | **1 GB** |
| Scale to zero | N/A | ❌ | ✅ |
| Model loading | HuggingFace download | HuggingFace download or `/opt/ml/model` | Same |

---

## References

- [AWS SageMaker: Use Your Own Inference Code](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html)
- [AWS SageMaker: Adapt Your Own Inference Container](https://docs.aws.amazon.com/sagemaker/latest/dg/adapt-inference-container.html)
- [AWS SageMaker Inference Toolkit (GitHub)](https://github.com/aws/sagemaker-inference-toolkit)
- [AWS SageMaker Examples — BYOC](https://github.com/aws/amazon-sagemaker-examples)
- [SageMaker Inference Toolkit — `parameters.py`](https://github.com/aws/sagemaker-pytorch-inference-toolkit/blob/master/src/sagemaker_inference/parameters.py) — defines `SAGEMAKER_BIND_TO_PORT`, `SAGEMAKER_MODEL_SERVER_TIMEOUT`, etc.
- [SageMaker Asynchronous Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)
- [SageMaker Streaming Inference](https://aws.amazon.com/blogs/machine-learning/elevating-the-generative-ai-experience-introducing-streaming-support-in-amazon-sagemaker-hosting/)
- [InvokeEndpoint timeout is hardcoded at 60s](https://github.com/aws/sagemaker-python-sdk/issues/1119)
