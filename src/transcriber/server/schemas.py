"""Request and response schemas for the transcription API.

Response models intentionally mirror a subset of
:class:`~transcriber.core.models.TranscriptSegment` and
:class:`~transcriber.core.models.TranscriptResult` — only the
fields relevant to API consumers are exposed (e.g. ``words``
is omitted from segments).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..core.models import TranscriptResult


class UTF8JSONResponse(JSONResponse):
    """JSONResponse that emits raw UTF-8 instead of ASCII escapes."""

    def render(self, content: Any) -> bytes:
        """Serialize *content* as UTF-8 JSON."""
        return json.dumps(content, ensure_ascii=False).encode("utf-8")


class TranscribeRequest(BaseModel):
    """JSON body for base64-encoded audio submission."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")
    diarize: bool = False


class SegmentResponse(BaseModel):
    """A single transcript segment (API view, without word-level detail)."""

    start: float
    end: float
    text: str
    speaker: str | None = None


class TranscribeResponse(BaseModel):
    """Transcription result returned to the client."""

    transcript: str
    segments: list[SegmentResponse] = Field(default_factory=list)
    language: str
    duration: float
    timings: dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_result(cls, result: TranscriptResult) -> TranscribeResponse:
        """Build a response from a pipeline :class:`TranscriptResult`.

        Args:
            result: Pipeline output.

        Returns:
            API-ready response model.
        """
        return cls(
            transcript=result.full_text,
            segments=[
                SegmentResponse(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    speaker=seg.speaker,
                )
                for seg in result.segments
            ],
            language=result.language,
            duration=result.duration,
            timings=result.timings,
        )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool
    model_size: str
    device: str
    queue_size: int = 0


# ---------------------------------------------------------------------------
# SSE events
# ---------------------------------------------------------------------------


class SSEProgressEvent(BaseModel):
    """Payload for ``event: progress`` SSE messages."""

    stage: str
    message: str


class SSECompleteEvent(BaseModel):
    """Payload for ``event: complete`` SSE messages."""

    transcript: str
    segments: list[SegmentResponse] = Field(default_factory=list)
    language: str
    duration: float
    timings: dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_result(cls, result: TranscriptResult) -> SSECompleteEvent:
        """Build from a pipeline :class:`TranscriptResult`."""
        return cls(
            transcript=result.full_text,
            segments=[
                SegmentResponse(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    speaker=seg.speaker,
                )
                for seg in result.segments
            ],
            language=result.language,
            duration=result.duration,
            timings=result.timings,
        )


class SSEErrorEvent(BaseModel):
    """Payload for ``event: error`` SSE messages."""

    detail: str


SSEEventType = Literal["progress", "complete", "error"]


def format_sse(event: SSEEventType, data: BaseModel) -> str:
    """Format a Pydantic model as an SSE text frame.

    Returns a string like::

        event: progress
        data: {"stage": "transcribe", ...}

    """
    return (
        f"event: {event}\ndata: {json.dumps(data.model_dump(), ensure_ascii=False)}\n\n"
    )
