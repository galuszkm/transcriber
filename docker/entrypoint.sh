#!/usr/bin/env bash
# =============================================================================
# Entrypoint for the transcriber inference container.
#
# SageMaker invokes the container with "serve" as the first argument.
# This script starts the FastAPI server via the trans-server entry point
# using environment variables for configuration.
#
# The SAGEMAKER_BIND and SAGEMAKER_PORT variables are set in the
# Dockerfile (0.0.0.0 and 8080 respectively).
# =============================================================================
set -euo pipefail

# SageMaker passes "serve" — just start the server regardless of args.
exec trans-server \
    --host "${SAGEMAKER_BIND}" \
    --port "${SAGEMAKER_PORT}" \
    --model "${MODEL:-large-v3}" \
    --device "${DEVICE:-cuda}" \
    --compute-type "${COMPUTE_TYPE:-auto}" \
    --batch-size "${BATCH_SIZE:-16}"
