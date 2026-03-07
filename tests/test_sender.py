"""Tests for transcriber.client.sender - SSE parsing logic."""

import pytest

from transcriber.client.sender import _parse_sse


class TestParseSSE:
    """SSE line-pair parsing state machine."""

    def test_complete_event_returns_data(self) -> None:
        lines = iter([
            "event: complete",
            'data: {"transcript": "hello"}',
            "",
        ])
        result = _parse_sse(lines, on_progress=None)
        assert result == {"transcript": "hello"}

    def test_error_event_raises(self) -> None:
        lines = iter([
            "event: error",
            'data: {"detail": "boom"}',
            "",
        ])
        with pytest.raises(RuntimeError, match="boom"):
            _parse_sse(lines, on_progress=None)

    def test_progress_callback_invoked(self) -> None:
        stages: list[tuple[str, str]] = []
        lines = iter([
            "event: progress",
            'data: {"stage": "transcribe", "message": "Working"}',
            "",
            "event: complete",
            'data: {"result": true}',
            "",
        ])
        result = _parse_sse(lines, on_progress=lambda s, m: stages.append((s, m)))
        assert result == {"result": True}
        assert stages == [("transcribe", "Working")]

    def test_stream_without_complete_raises(self) -> None:
        lines = iter([
            "event: progress",
            'data: {"stage": "loading", "message": "..."}',
            "",
        ])
        with pytest.raises(RuntimeError, match="complete"):
            _parse_sse(lines, on_progress=None)

    def test_keepalive_comments_ignored(self) -> None:
        lines = iter([
            ": keepalive",
            "event: complete",
            'data: {"ok": true}',
            "",
        ])
        result = _parse_sse(lines, on_progress=None)
        assert result == {"ok": True}

    def test_multiple_progress_events(self) -> None:
        stages: list[str] = []
        lines = iter([
            "event: progress",
            'data: {"stage": "load", "message": "a"}',
            "",
            "event: progress",
            'data: {"stage": "transcribe", "message": "b"}',
            "",
            "event: complete",
            'data: {"done": true}',
            "",
        ])
        _parse_sse(lines, on_progress=lambda s, m: stages.append(s))
        assert stages == ["load", "transcribe"]
