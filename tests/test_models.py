"""Tests for transcriber.core.models - data model logic."""

from transcriber.core.models import TranscriptResult, TranscriptSegment


class TestTranscriptResultFullText:
    """full_text property concatenates segments correctly."""

    def test_empty_segments(self) -> None:
        result = TranscriptResult(source_file="x.wav", language="en")
        assert result.full_text == ""

    def test_single_segment(self) -> None:
        result = TranscriptResult(
            source_file="x.wav",
            language="en",
            segments=[TranscriptSegment(start=0, end=1, text="  Hello  ")],
        )
        assert result.full_text == "Hello"

    def test_multiple_segments_joined(self) -> None:
        result = TranscriptResult(
            source_file="x.wav",
            language="en",
            segments=[
                TranscriptSegment(start=0, end=1, text="Hello"),
                TranscriptSegment(start=1, end=2, text="world"),
            ],
        )
        assert result.full_text == "Hello world"

    def test_whitespace_stripped_per_segment(self) -> None:
        result = TranscriptResult(
            source_file="x.wav",
            language="en",
            segments=[
                TranscriptSegment(start=0, end=1, text="  A  "),
                TranscriptSegment(start=1, end=2, text="  B  "),
            ],
        )
        assert result.full_text == "A B"
