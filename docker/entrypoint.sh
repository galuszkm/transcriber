#!/usr/bin/env bash
# =============================================================================
# Entrypoint for the transcriber inference container.
#
# SageMaker invokes the container with "serve" as the first argument.
# This script starts the FastAPI server via the trans-server entry point.
# The server defaults to 0.0.0.0:8080, which satisfies the SageMaker
# container contract out of the box.
# =============================================================================
set -euo pipefail

# SageMaker passes "serve" — just start the server regardless of args.
exec trans-server \
    --model "${MODEL:-large-v3}" \
    --device "${DEVICE:-cuda}" \
    --compute-type "${COMPUTE_TYPE:-auto}" \
    --batch-size "${BATCH_SIZE:-16}"
