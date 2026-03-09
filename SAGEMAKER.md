# Deploying on AWS SageMaker

The transcription server supports deployment on [AWS SageMaker](https://aws.amazon.com/sagemaker/) as a **Bring Your Own Container (BYOC)** endpoint.  The server already satisfies the SageMaker container contract out of the box — it listens on port 8080, exposes `GET /ping` for health checks, and accepts inference requests at `POST /invocations`.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Build the Docker Image](#build-the-docker-image)
3. [Push Image to ECR](#push-image-to-ecr)
4. [Deployment Options](#deployment-options)
   - [Real-Time Endpoint](#real-time-endpoint)
   - [Asynchronous Endpoint](#asynchronous-endpoint)
5. [Invoking the Endpoint](#invoking-the-endpoint)
   - [Real-Time Invocation](#real-time-invocation)
   - [Async Invocation](#async-invocation)
6. [Available Endpoints](#available-endpoints)
7. [Limitations](#limitations)
8. [References](#references)

---

## Prerequisites

- Docker installed and running
- AWS CLI configured (`aws configure`)
- An Amazon ECR repository for the image
- An IAM role with `AmazonSageMakerFullAccess` (or equivalent)
- *(For speaker diarization)* A free HuggingFace token — see [README § Getting a HuggingFace token](README.md#getting-a-huggingface-token-for-speaker-diarization)

---

## Build the Docker Image

A `Dockerfile` is included at the repository root.  It uses an NVIDIA CUDA base image and installs all Python dependencies via `uv`.

```bash
# Build
docker build -t transcriber-inference .

# Verify locally (GPU)
docker run --gpus all -p 8080:8080 transcriber-inference

# Verify locally (CPU)
docker run -p 8080:8080 -e DEVICE=cpu transcriber-inference

# Health check
curl http://localhost:8080/ping
# → {"status":"loading",...}  (until the model finishes loading)

# Inference test
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/octet-stream" \
  --data-binary @audio.wav
```

Environment variables you can pass to `docker run -e`:

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL` | Whisper model size (`tiny` … `large-v3`) | `large-v3` |
| `DEVICE` | `cuda` or `cpu` | `cuda` |
| `HF_TOKEN` | HuggingFace token (required only for diarization) | — |
| `CACHE_DIR` | Path to pre-cached model files | `.cache` |

---

## Push Image to ECR

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
REPO=transcriber-inference

# Create repository (first time only)
aws ecr create-repository --repository-name $REPO --region $REGION

# Authenticate
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
    $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag and push
docker tag transcriber-inference:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
```

---

## Deployment Options

### Choosing an Endpoint Type

| | Real-Time | Asynchronous |
|---|---|---|
| **Max inference time** | 60 seconds | Up to 1 hour |
| **Max payload** | 25 MB | Up to 1 GB (via S3) |
| **Response delivery** | Synchronous (inline) | Asynchronous (S3 output) |
| **Scale to zero** | ❌ | ✅ (cost savings when idle) |
| **Best for** | Short clips, fast responses | Long recordings, large files |

Both endpoint types use the **exact same container image** — no code changes needed.

---

### Real-Time Endpoint

Suitable for audio files up to ~25 MB that transcribe within 60 seconds.

#### Step 1: Register the Model

```python
import boto3

sm = boto3.client("sagemaker", region_name="us-east-1")
account_id = boto3.client("sts").get_caller_identity()["Account"]
region = "us-east-1"

sm.create_model(
    ModelName="transcriber-model",
    PrimaryContainer={
        "Image": f"{account_id}.dkr.ecr.{region}.amazonaws.com/transcriber-inference:latest",
        "Environment": {
            "MODEL": "large-v3",
            "DEVICE": "cuda",
            # "HF_TOKEN": "hf_...",  # Uncomment to enable speaker diarization
        },
    },
    ExecutionRoleArn=f"arn:aws:iam::{account_id}:role/SageMakerExecutionRole",
)
```

#### Step 2: Create Endpoint Configuration

```python
sm.create_endpoint_config(
    EndpointConfigName="transcriber-realtime-config",
    ProductionVariants=[
        {
            "VariantName": "primary",
            "ModelName": "transcriber-model",
            "InstanceType": "ml.g5.xlarge",          # NVIDIA A10G GPU
            "InitialInstanceCount": 1,
            "ContainerStartupHealthCheckTimeoutInSeconds": 600,  # Allow time for model download
        },
    ],
)
```

#### Step 3: Deploy

```python
sm.create_endpoint(
    EndpointName="transcriber-endpoint",
    EndpointConfigName="transcriber-realtime-config",
)

# Wait for the endpoint to become active (5–10 minutes on first deploy)
waiter = sm.get_waiter("endpoint_in_service")
waiter.wait(EndpointName="transcriber-endpoint")
print("Endpoint is ready")
```

---

### Asynchronous Endpoint

For longer recordings or larger files.  SageMaker reads the audio from S3, calls `/invocations`, and writes the result back to S3.  The same model registration from the real-time steps above is reused.

#### Step 1: Create Async Endpoint Configuration

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
            # Optional SNS notifications on completion or error:
            # "NotificationConfig": {
            #     "SuccessTopic": "arn:aws:sns:us-east-1:123456789:TranscribeSuccess",
            #     "ErrorTopic":   "arn:aws:sns:us-east-1:123456789:TranscribeError",
            # },
        },
        "ClientConfig": {
            "MaxConcurrentInvocationsPerInstance": 1,  # One job at a time per GPU
        },
    },
)
```

#### Step 2: Deploy

```python
sm.create_endpoint(
    EndpointName="transcriber-async-endpoint",
    EndpointConfigName="transcriber-async-config",
)

waiter = sm.get_waiter("endpoint_in_service")
waiter.wait(EndpointName="transcriber-async-endpoint")
print("Async endpoint is ready")
```

> **Scale-to-zero**: Async endpoints can scale down to zero instances when idle, saving cost.  Use `update_endpoint_weights_and_capacities` or auto-scaling policies to configure this.

---

## Invoking the Endpoint

### Real-Time Invocation

```python
import boto3, json

runtime = boto3.client("sagemaker-runtime", region_name="us-east-1")

# Option A — raw audio bytes
with open("audio.wav", "rb") as f:
    response = runtime.invoke_endpoint(
        EndpointName="transcriber-endpoint",
        ContentType="application/octet-stream",
        Body=f.read(),
    )
result = json.loads(response["Body"].read())
print(result["transcript"])

# Option B — base64-encoded JSON (useful when the caller cannot send binary)
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

**Response shape:**

```json
{
  "transcript": "Full text of the recording...",
  "segments": [
    {"start": 0.5, "end": 2.1, "text": "Hello everyone.", "speaker": "SPEAKER_00"}
  ],
  "language": "en",
  "duration": 45.2,
  "timings": {"model_load": 0.01, "transcribe": 3.2}
}
```

---

### Async Invocation

```python
import boto3, json, time

s3      = boto3.client("s3",                  region_name="us-east-1")
runtime = boto3.client("sagemaker-runtime",   region_name="us-east-1")

BUCKET = "my-bucket"

# 1. Upload audio to S3
s3.upload_file("long_meeting.wav", BUCKET, "inputs/long_meeting.wav")

# 2. Submit the job — returns immediately
response = runtime.invoke_endpoint_async(
    EndpointName="transcriber-async-endpoint",
    InputLocation=f"s3://{BUCKET}/inputs/long_meeting.wav",
    ContentType="application/octet-stream",
    InvocationTimeoutSeconds=3600,   # up to 1 hour
)
output_location = response["OutputLocation"]
print(f"Job submitted — result will appear at: {output_location}")

# 3. Poll S3 for the result (or use SNS to get notified)
bucket, key = output_location.replace("s3://", "").split("/", 1)
while True:
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        result = json.loads(obj["Body"].read())
        print(result["transcript"])
        break
    except s3.exceptions.NoSuchKey:
        print("Waiting for result...")
        time.sleep(15)
```

---

## Available Endpoints

All endpoints are available at the container level (locally or on SageMaker):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping` | GET | Health check — `200` (ready) / `503` (model loading) |
| `/health` | GET | Identical to `/ping` |
| `/invocations` | POST | SageMaker inference — auto-detects `Content-Type` |
| `/transcribe` | POST | Multipart form or base64 upload |
| `/transcribe/json` | POST | JSON body with base64-encoded audio |
| `/transcribe/raw` | POST | Raw audio bytes |
| `/transcribe/stream` | POST | SSE streaming (progress + result) |
| `/transcribe/json/stream` | POST | SSE streaming with JSON input |
| `/transcribe/raw/stream` | POST | SSE streaming with raw bytes |
| `/ws/transcribe` | WebSocket | Continuous transcription (not available on SageMaker) |

`/invocations` accepts the following `Content-Type` values:

| Content-Type | Input |
|---|---|
| `application/octet-stream` | Raw audio bytes |
| `application/json` | `{"audio_base64": "...", "diarize": false}` |
| `multipart/form-data` | `file` field (audio file upload) |

---

## Limitations

| Feature | Real-Time | Async |
|---------|-----------|-------|
| WebSocket (`/ws/transcribe`) | ❌ Not supported by SageMaker | ❌ Not supported |
| SSE streaming | ⚠️ Via `InvokeEndpointWithResponseStream` (8 min timeout) | ❌ Not applicable |
| Inference timeout | **60 seconds** (hardcoded) | Up to **1 hour** |
| Max payload | **25 MB** | Up to **1 GB** |
| Scale to zero | ❌ | ✅ |

---

## References

- [AWS SageMaker: Use Your Own Inference Code](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html)
- [AWS SageMaker: Asynchronous Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)
- [SageMaker Inference Toolkit (GitHub)](https://github.com/aws/sagemaker-inference-toolkit)
- [SageMaker Examples — BYOC (GitHub)](https://github.com/aws/amazon-sagemaker-examples)
- [InvokeEndpointWithResponseStream API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpointWithResponseStream.html)
- [60-second real-time timeout — confirmed limitation](https://github.com/aws/sagemaker-python-sdk/issues/1119)
