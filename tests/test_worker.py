"""Tests for transcriber.server.worker - inference worker logic."""

import asyncio

from transcriber.core.config import TranscriptionConfig
from transcriber.server.schemas import SSEErrorEvent
from transcriber.server.worker import InferenceWorker


class TestInferenceWorkerInit:
    """Worker initialization and property checks."""

    def test_not_ready_before_start(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        worker = InferenceWorker(cfg)
        assert worker.is_ready is False

    def test_queue_size_zero_initially(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        worker = InferenceWorker(cfg)
        assert worker.queue_size == 0


class TestMakeProgressFn:
    """_make_progress_fn builds a thread-safe SSE progress callback."""

    def test_returns_none_when_no_queue(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            result = InferenceWorker._make_progress_fn(loop, None)
            assert result is None
        finally:
            loop.close()

    def test_returns_callable_with_queue(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            fn = InferenceWorker._make_progress_fn(loop, queue)
            assert callable(fn)
        finally:
            loop.close()


class TestSendSSE:
    """_send_sse pushes final event + sentinel."""

    def test_none_queue_is_noop(self) -> None:
        evt = SSEErrorEvent(detail="test")
        InferenceWorker._send_sse(None, "error", evt)

    def test_sends_event_and_sentinel(self) -> None:
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        evt = SSEErrorEvent(detail="boom")
        InferenceWorker._send_sse(queue, "error", evt)
        assert queue.qsize() == 2
        frame = queue.get_nowait()
        assert frame is not None
        assert "error" in frame
        assert "boom" in frame
        sentinel = queue.get_nowait()
        assert sentinel is None
