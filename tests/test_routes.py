"""Tests for transcriber.server.routes - SSE generator and route helpers."""

import asyncio
from unittest.mock import MagicMock, PropertyMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from transcriber.server.routes import _sse_generator, router
from transcriber.server.schemas import UTF8JSONResponse


@pytest.mark.asyncio
async def test_sse_generator_yields_frames() -> None:
    """Generator yields frames and stops at None sentinel."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    queue.put_nowait("event: progress\ndata: {}\n\n")
    queue.put_nowait("event: complete\ndata: {}\n\n")
    queue.put_nowait(None)

    frames = []
    async for frame in _sse_generator(queue):
        frames.append(frame)

    assert len(frames) == 2
    assert "progress" in frames[0]
    assert "complete" in frames[1]


@pytest.mark.asyncio
async def test_sse_generator_stops_on_none() -> None:
    """Generator terminates when it receives None."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    queue.put_nowait(None)

    frames = []
    async for frame in _sse_generator(queue):
        frames.append(frame)

    assert frames == []


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_test_app(*, worker_ready: bool = True) -> FastAPI:
    """Build a minimal FastAPI app with a mocked worker for route testing."""
    app = FastAPI(default_response_class=UTF8JSONResponse)
    worker = MagicMock()
    type(worker).is_ready = PropertyMock(return_value=worker_ready)
    type(worker).queue_size = PropertyMock(return_value=0)

    config = MagicMock()
    config.model = "large-v3"
    config.device = "cpu"

    app.state.worker = worker
    app.state.config = config
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# /ping and /health — unified health check
# ---------------------------------------------------------------------------


class TestPingEndpoint:
    """GET /ping — health check returning HealthResponse."""

    def test_ping_returns_200_when_ready(self) -> None:
        app = _make_test_app(worker_ready=True)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["model_loaded"] is True

    def test_ping_returns_503_when_loading(self) -> None:
        app = _make_test_app(worker_ready=False)
        client = TestClient(app)
        resp = client.get("/ping")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "loading"
        assert body["model_loaded"] is False


class TestHealthEndpoint:
    """GET /health — same handler as /ping."""

    def test_health_returns_200_when_ready(self) -> None:
        app = _make_test_app(worker_ready=True)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["model_size"] == "large-v3"
        assert body["device"] == "cpu"

    def test_health_returns_503_when_loading(self) -> None:
        app = _make_test_app(worker_ready=False)
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "loading"


# ---------------------------------------------------------------------------
# /invocations — SageMaker inference
# ---------------------------------------------------------------------------


class TestInvocationsEndpoint:
    """POST /invocations — SageMaker inference."""

    def test_empty_body_returns_400(self) -> None:
        app = _make_test_app()
        client = TestClient(app)
        resp = client.post("/invocations", content=b"")
        assert resp.status_code == 400
        assert "Empty request body" in resp.json()["detail"]

    def test_json_missing_audio_base64_returns_400(self) -> None:
        app = _make_test_app()
        client = TestClient(app)
        resp = client.post(
            "/invocations",
            json={"diarize": False},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert "audio_base64" in resp.json()["detail"]

    def test_multipart_missing_file_returns_400(self) -> None:
        app = _make_test_app()
        client = TestClient(app)
        # Send multipart form without the required "file" field.
        resp = client.post(
            "/invocations",
            files={"not_a_file": ("dummy.txt", b"data")},
        )
        assert resp.status_code == 400
