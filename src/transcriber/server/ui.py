"""Serve the pre-built React UI at ``/ui``.

Static assets are served with a 1-hour ``Cache-Control`` header.
``index.html`` is served with ``no-cache`` so the browser always
fetches the latest entry point while long-caching hashed bundles.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

_CACHE_MAX_AGE = 3600  # 1 hour


class _CachedStaticFiles(StaticFiles):
    """StaticFiles subclass that adds Cache-Control headers."""

    async def get_response(self, path: str, scope: dict) -> Response:  # type: ignore[override]
        """Return response with cache-control header."""
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = (
                f"public, max-age={_CACHE_MAX_AGE}"
            )
        return response


def mount_ui(app: FastAPI, static_dir: Path) -> None:
    """Mount the UI on ``/ui`` with proper cache headers.

    Args:
        app: The FastAPI application instance.
        static_dir: Path to the directory with built UI files.
    """
    index_html = static_dir / "index.html"

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    async def _serve_ui(request: Request) -> HTMLResponse:
        """Serve the SPA index.html (no-cache so updates propagate)."""
        return HTMLResponse(
            content=index_html.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-cache"},
        )

    app.mount(
        "/ui",
        _CachedStaticFiles(directory=str(static_dir), html=False),
        name="ui-static",
    )

    logger.info("UI mounted at /ui (static root: %s)", static_dir)
