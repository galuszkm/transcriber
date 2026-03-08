# =============================================================================
# Dockerfile — transcriber inference container (SageMaker-compatible)
# =============================================================================
#
# Builds a GPU-ready container that satisfies the AWS SageMaker Bring Your
# Own Container (BYOC) contract:
#   • Listens on port 8080
#   • Exposes GET /ping   (health check)
#   • Exposes POST /invocations (inference)
#
# It also keeps every original endpoint (/health, /transcribe, etc.) so the
# same image works locally and on SageMaker.
#
# Build:
#   docker build -t transcriber-inference .
#
# Run locally:
#   docker run --gpus all -p 8080:8080 transcriber-inference
#
# See SAGEMAKER.md for full deployment instructions.
# =============================================================================

FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu24.04

# ---- system dependencies ----------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv git ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# ---- Python environment -----------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /usr/local/bin/uv

WORKDIR /opt/program

# Copy project files
COPY pyproject.toml ./
COPY src/ src/

# Install the package with server + ML extras
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install --extra server "." \
        --index-url https://pypi.org/simple/ \
        --extra-index-url https://download.pytorch.org/whl/cu128

ENV PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV="/opt/venv"

# ---- SageMaker contract -----------------------------------------------------
# SageMaker mounts model artifacts here (when supplied via S3 model.tar.gz).
# The transcriber also supports downloading models from HuggingFace at
# startup, so this directory may remain empty if models are baked in or
# fetched on the fly.
ENV SM_MODEL_DIR=/opt/ml/model
RUN mkdir -p /opt/ml/model

# SageMaker requires the container to listen on port 8080.
ENV SAGEMAKER_PORT=8080 \
    SAGEMAKER_BIND=0.0.0.0

EXPOSE 8080

# ---- entrypoint --------------------------------------------------------------
# SageMaker invokes the container with "serve" as the first argument.
# We use a small shell wrapper that ignores unknown arguments and starts
# the FastAPI server on port 8080 bound to 0.0.0.0.
COPY docker/entrypoint.sh /opt/program/entrypoint.sh
RUN chmod +x /opt/program/entrypoint.sh

ENTRYPOINT ["/opt/program/entrypoint.sh"]
CMD ["serve"]
