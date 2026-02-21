"""Pydantic data models for transcription results.

Defines :class:`TranscriptSegment` and :class:`TranscriptResult`,
the typed value objects that flow through the pipeline and are
consumed by the output formatters.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """A single segment of transcribed speech.

    Attributes:
        start: Segment start time in seconds.
        end: Segment end time in seconds.
        text: Transcribed text content.
        speaker: Speaker label (e.g. ``"SPEAKER_00"``), or ``None``
            when diarization was not used.
        words: Optional word-level timing data from alignment.
    """

    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[dict[str, float | str]] = Field(default_factory=list)


class TranscriptResult(BaseModel):
    """Complete transcription result for an audio file.

    Attributes:
        source_file: Path to the original audio file.
        language: Detected or specified ISO language code.
        segments: Ordered list of transcript segments.
        duration: Total audio duration in seconds.
        timings: Per-step wall-clock measurements (seconds).
    """

    source_file: str
    language: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    duration: float = 0.0
    timings: dict[str, float] = Field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenate all segment texts into a single string."""
        return " ".join(seg.text.strip() for seg in self.segments)
