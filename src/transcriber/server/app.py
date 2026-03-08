"""FastAPI application factory with lifespan-managed inference worker.

Start the server::

    trans-server                               # defaults
    trans-server --model large-v3 --port 9000  # custom
    trans-server --device cpu                  # CPU mode

The server binds to ``0.0.0.0:8080`` by default, which satisfies the
AWS SageMaker container contract out of the box.  SageMaker-compatible
``GET /ping`` and ``POST /invocations`` routes are always registered.

See ``SAGEMAKER.md`` in the repository root for a full deployment guide.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..cli.parser import add_pipeline_args
from ..core.config import TranscriptionConfig
from .routes import router
from .schemas import UTF8JSONResponse
from .worker import InferenceWorker

logger = logging.getLogger(__name__)


def create_app(config: TranscriptionConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Pipeline configuration.  Defaults to CUDA / large-v3 model.

    Returns:
        Configured FastAPI application instance.
    """
    config = config or TranscriptionConfig()
    worker = InferenceWorker(config)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await worker.start()
        yield
        await worker.stop()

    app = FastAPI(
        title="Transcription Service",
        lifespan=lifespan,
        default_response_class=UTF8JSONResponse,
    )
    app.state.worker = worker
    app.state.config = config
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``trans-server``.

    Reuses the shared pipeline arguments from :func:`add_pipeline_args`
    and adds server-specific ``--host`` / ``--port`` options.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        description="Start the transcription service.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",  # noqa: S104  # nosec B104
        help="Bind host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Bind port (default: 8080)",
    )

    add_pipeline_args(parser, default_device="cuda")

    return parser


def main() -> None:
    """CLI entry point for ``trans-server``."""
    import uvicorn

    args = _build_parser().parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    overrides: dict = {
        "model": args.model,
        "device": args.device,
        "compute_type": args.compute_type,
        "batch_size": args.batch_size,
        "diarize": False,
    }
    if args.hf_token is not None:
        overrides["hf_token"] = args.hf_token
    if args.cache_dir is not None:
        overrides["cache_dir"] = args.cache_dir
    config = TranscriptionConfig(**overrides)

    app = create_app(config)
    uvicorn.run(app, host=args.host, port=args.port)
