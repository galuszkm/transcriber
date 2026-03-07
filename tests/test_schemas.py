"""Tests for transcriber.server.schemas - SSE formatting and response conversion."""

import json

from transcriber.core.models import TranscriptResult, TranscriptSegment
from transcriber.server.schemas import (
    SSECompleteEvent,
    SSEErrorEvent,
    SSEProgressEvent,
    TranscribeResponse,
    UTF8JSONResponse,
    format_sse,
)


def _make_result() -> TranscriptResult:
    return TranscriptResult(
        source_file="test.wav",
        language="en",
        segments=[
            TranscriptSegment(
                start=0.0, end=1.5, text="Hello world", speaker="SPEAKER_00"
            ),
            TranscriptSegment(start=1.5, end=3.0, text="Goodbye", speaker="SPEAKER_01"),
        ],
        duration=3.0,
        timings={"transcribe": 1.2},
    )


# ---------------------------------------------------------------------------
# format_sse
# ---------------------------------------------------------------------------


class TestFormatSSE:
    """SSE text-frame formatting."""

    def test_progress_event_format(self) -> None:
        evt = SSEProgressEvent(stage="transcribe", message="Working...")
        text = format_sse("progress", evt)
        assert text.startswith("event: progress\n")
        assert "data: " in text
        assert text.endswith("\n\n")
        payload = json.loads(text.split("data: ", 1)[1].strip())
        assert payload["stage"] == "transcribe"

    def test_error_event_format(self) -> None:
        evt = SSEErrorEvent(detail="Something broke")
        text = format_sse("error", evt)
        assert "event: error" in text
        payload = json.loads(text.split("data: ", 1)[1].strip())
        assert payload["detail"] == "Something broke"

    def test_complete_event_format(self) -> None:
        result = _make_result()
        evt = SSECompleteEvent.from_result(result)
        text = format_sse("complete", evt)
        assert "event: complete" in text

    def test_unicode_preserved(self) -> None:
        """Non-ASCII chars are not escaped in SSE payload."""
        evt = SSEProgressEvent(stage="transcribe", message="Cześć")
        text = format_sse("progress", evt)
        assert "Cześć" in text


# ---------------------------------------------------------------------------
# TranscribeResponse.from_result
# ---------------------------------------------------------------------------


class TestTranscribeResponseFromResult:
    """Pipeline result → API response conversion."""

    def test_transcript_is_full_text(self) -> None:
        result = _make_result()
        resp = TranscribeResponse.from_result(result)
        assert resp.transcript == "Hello world Goodbye"

    def test_segment_count_matches(self) -> None:
        result = _make_result()
        resp = TranscribeResponse.from_result(result)
        assert len(resp.segments) == 2

    def test_segment_fields_mapped(self) -> None:
        result = _make_result()
        resp = TranscribeResponse.from_result(result)
        seg = resp.segments[0]
        assert seg.start == 0.0
        assert seg.end == 1.5
        assert seg.text == "Hello world"
        assert seg.speaker == "SPEAKER_00"

    def test_duration_and_timings_mapped(self) -> None:
        result = _make_result()
        resp = TranscribeResponse.from_result(result)
        assert resp.duration == 3.0
        assert resp.timings == {"transcribe": 1.2}


# ---------------------------------------------------------------------------
# SSECompleteEvent.from_result
# ---------------------------------------------------------------------------


class TestSSECompleteEventFromResult:
    """Pipeline result → SSE complete event conversion."""

    def test_transcript_is_full_text(self) -> None:
        result = _make_result()
        evt = SSECompleteEvent.from_result(result)
        assert evt.transcript == "Hello world Goodbye"

    def test_segment_count_matches(self) -> None:
        result = _make_result()
        evt = SSECompleteEvent.from_result(result)
        assert len(evt.segments) == 2


# ---------------------------------------------------------------------------
# UTF8JSONResponse
# ---------------------------------------------------------------------------


class TestUTF8JSONResponse:
    """UTF-8 JSON response rendering."""

    def test_non_ascii_not_escaped(self) -> None:
        resp = UTF8JSONResponse(content={"msg": "Cześć"})
        body = bytes(resp.body).decode("utf-8")
        assert "Cześć" in body
        assert "\\u" not in body
