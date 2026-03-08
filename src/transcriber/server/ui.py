"""Serve the pre-built React UI at ``/ui``.

Static assets are served with a 1-hour ``Cache-Control`` header.
``index.html`` is served with ``no-cache`` and has server configuration
injected as ``window.__SERVER_CONFIG__`` so the React app can resolve
API URLs correctly behind reverse proxies.
"""

from __future__ import annotations

import json
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
            response.headers["Cache-Control"] = f"public, max-age={_CACHE_MAX_AGE}"
        return response


def mount_ui(app: FastAPI, static_dir: Path) -> None:
    """Mount the UI on ``/ui`` with proper cache headers.

    Server configuration (``apiBaseUrl``, ``staticUrl``) is injected into
    ``index.html`` as a ``<script>`` tag so the React app can read it from
    ``window.__SERVER_CONFIG__``.  This makes the UI work correctly behind
    reverse proxies and load balancers where the client-facing URL differs
    from the internal server URL.

    Args:
        app: The FastAPI application instance.
        static_dir: Path to the directory with built UI files.
    """
    index_html = (static_dir / "index.html").read_text(encoding="utf-8")

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    async def _serve_ui(request: Request) -> HTMLResponse:
        """Serve the SPA index.html with injected server config."""
        base = str(request.base_url).rstrip("/")
        # ensure_ascii=True escapes all non-ASCII chars; replace </
        # to prevent script injection via closing tags.
        config = json.dumps(
            {"apiBaseUrl": base, "staticUrl": f"{base}/ui"},
        ).replace("</", r"<\/")
        config_tag = f"<script>window.__SERVER_CONFIG__={config};</script>"
        html = index_html.replace("</head>", f"{config_tag}</head>", 1)
        return HTMLResponse(
            content=html,
            headers={"Cache-Control": "no-cache"},
        )

    app.mount(
        "/ui",
        _CachedStaticFiles(directory=str(static_dir), html=False),
        name="ui-static",
    )

    logger.info("UI mounted at /ui (static root: %s)", static_dir)
