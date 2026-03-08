"""Serve the pre-built React UI at ``/ui``.

Static assets are served with a 1-hour ``Cache-Control`` header.
``index.html`` is rendered as a Jinja2 template so the server can
inject configuration (API base URL, static URL) that the React app
reads from ``window.__SERVER_CONFIG__``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

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

    The ``index.html`` is rendered as a Jinja2 template receiving
    ``server_config_json`` - a JSON string with ``apiBaseUrl`` and
    ``staticUrl`` that the React app reads from ``window.__SERVER_CONFIG__``.

    Args:
        app: The FastAPI application instance.
        static_dir: Path to the directory with built UI files.
    """
    env = Environment(
        loader=FileSystemLoader(str(static_dir)),
        autoescape=True,
    )
    template = env.get_template("index.html")

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    async def _serve_ui(request: Request) -> HTMLResponse:
        """Serve the SPA index.html with injected server config."""
        base = str(request.base_url).rstrip("/")
        config = {
            "apiBaseUrl": base,
            "staticUrl": f"{base}/ui",
        }
        html = template.render(server_config_json=json.dumps(config))
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
