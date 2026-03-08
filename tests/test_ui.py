"""Tests for transcriber.server.ui - static UI serving."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from transcriber.server.ui import mount_ui


@pytest.fixture()
def static_dir(tmp_path: Path) -> Path:
    """Create a minimal static directory with an index.html."""
    (tmp_path / "index.html").write_text(
        "<html><head>"
        '<script type="module" crossorigin src="./js/index.js"></script>'
        '<link rel="stylesheet" crossorigin href="./css/index.css">'
        "</head><body><div>hello</div></body></html>",
        encoding="utf-8",
    )
    css = tmp_path / "css"
    css.mkdir()
    (css / "index.css").write_text("body{}", encoding="utf-8")
    js = tmp_path / "js"
    js.mkdir()
    (js / "index.js").write_text("console.log('ok')", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def app_with_ui(static_dir: Path) -> FastAPI:
    """Bare FastAPI app with UI mounted."""
    app = FastAPI()
    mount_ui(app, static_dir)
    return app


class TestMountUI:
    """UI endpoint tests."""

    def test_ui_returns_index_html(self, app_with_ui: FastAPI) -> None:
        client = TestClient(app_with_ui)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "hello" in resp.text
        assert resp.headers["cache-control"] == "no-cache"

    def test_ui_injects_server_config(self, app_with_ui: FastAPI) -> None:
        client = TestClient(app_with_ui)
        resp = client.get("/")
        assert "__SERVER_CONFIG__" in resp.text
        assert "apiBaseUrl" in resp.text
        assert "staticUrl" in resp.text

    def test_static_css(self, app_with_ui: FastAPI) -> None:
        client = TestClient(app_with_ui)
        resp = client.get("/static/css/index.css")
        assert resp.status_code == 200
        assert "body" in resp.text
        assert "max-age=3600" in resp.headers["cache-control"]

    def test_static_js(self, app_with_ui: FastAPI) -> None:
        client = TestClient(app_with_ui)
        resp = client.get("/static/js/index.js")
        assert resp.status_code == 200
        assert "console" in resp.text
        assert "max-age=3600" in resp.headers["cache-control"]

    def test_asset_paths_rewritten_to_static(self, app_with_ui: FastAPI) -> None:
        client = TestClient(app_with_ui)
        resp = client.get("/")
        assert 'src="/static/js/index.js"' in resp.text
        assert 'href="/static/css/index.css"' in resp.text
        assert "./js/" not in resp.text
        assert "./css/" not in resp.text

    def test_missing_asset_returns_404(self, app_with_ui: FastAPI) -> None:
        client = TestClient(app_with_ui)
        resp = client.get("/static/nonexistent.js")
        assert resp.status_code == 404
