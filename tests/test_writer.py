"""Tests for transcriber.io.writer - rendering and file output."""

from pathlib import Path
from typing import Any

from transcriber.core.models import TranscriptResult, TranscriptSegment
from transcriber.io.writer import (
    OutputFormat,
    TranscriptWriter,
    _markdown_speaker_blocks,
    format_timestamp,
)

# ---------------------------------------------------------------------------
# format_timestamp
# ---------------------------------------------------------------------------


class TestFormatTimestamp:
    """Edge cases and boundary logic in format_timestamp."""

    def test_zero_seconds(self) -> None:
        assert format_timestamp(0) == "00:00"

    def test_seconds_only(self) -> None:
        assert format_timestamp(45) == "00:45"

    def test_minutes_and_seconds(self) -> None:
        assert format_timestamp(125) == "02:05"

    def test_exactly_one_hour(self) -> None:
        assert format_timestamp(3600) == "1:00:00"

    def test_hours_minutes_seconds(self) -> None:
        assert format_timestamp(3661) == "1:01:01"

    def test_large_value(self) -> None:
        # 10 hours + 5 min + 30 sec
        assert format_timestamp(36330) == "10:05:30"

    def test_fractional_seconds_truncated(self) -> None:
        assert format_timestamp(59.9) == "00:59"


# ---------------------------------------------------------------------------
# Markdown rendering - speaker grouping
# ---------------------------------------------------------------------------


def _make_result(
    segments: list[TranscriptSegment] | None = None,
    **kwargs: Any,
) -> TranscriptResult:
    defaults: dict[str, Any] = {
        "source_file": "meeting.wav",
        "language": "en",
        "segments": segments or [],
        "duration": 120.0,
    }
    defaults.update(kwargs)
    return TranscriptResult(**defaults)


class TestMarkdownSpeakerBlocks:
    """Speaker-change grouping in _markdown_speaker_blocks."""

    def test_consecutive_same_speaker_merged(self) -> None:
        segs = [
            TranscriptSegment(start=0, end=5, text="Hello world", speaker="SPEAKER_00"),
            TranscriptSegment(
                start=5, end=10, text="How are you?", speaker="SPEAKER_00"
            ),
        ]
        result = _make_result(segs)
        lines = _markdown_speaker_blocks(result)
        # Only one speaker header for both segments
        headers = [ln for ln in lines if ln.startswith("**SPEAKER_00**")]
        assert len(headers) == 1

    def test_speaker_change_creates_new_block(self) -> None:
        segs = [
            TranscriptSegment(start=0, end=5, text="Hi", speaker="SPEAKER_00"),
            TranscriptSegment(start=5, end=10, text="Hey", speaker="SPEAKER_01"),
        ]
        result = _make_result(segs)
        lines = _markdown_speaker_blocks(result)
        headers = [ln for ln in lines if ln.startswith("**SPEAKER_0")]
        assert len(headers) == 2

    def test_no_speaker_uses_fallback_label(self) -> None:
        segs = [TranscriptSegment(start=0, end=5, text="Text", speaker=None)]
        result = _make_result(segs)
        lines = _markdown_speaker_blocks(result)
        assert any("**Speaker**" in ln for ln in lines)


# ---------------------------------------------------------------------------
# Full rendering
# ---------------------------------------------------------------------------


class TestTranscriptWriter:
    """Integration-level writer tests."""

    def test_render_markdown_no_segments(self) -> None:
        writer = TranscriptWriter(OutputFormat.MARKDOWN)
        result = _make_result()
        md = writer.render(result)
        assert "*No speech detected.*" in md

    def test_render_markdown_with_segments(self) -> None:
        segs = [
            TranscriptSegment(start=0, end=5, text="Hello world", speaker="SPEAKER_00"),
        ]
        writer = TranscriptWriter(OutputFormat.MARKDOWN)
        md = writer.render(_make_result(segs))
        assert "Hello world" in md
        assert "# Transcript:" in md

    def test_render_json_roundtrip(self) -> None:
        import json

        segs = [TranscriptSegment(start=1.0, end=2.5, text="Test")]
        writer = TranscriptWriter(OutputFormat.JSON)
        raw = writer.render(_make_result(segs))
        data = json.loads(raw)
        assert data["language"] == "en"
        assert len(data["segments"]) == 1
        assert data["segments"][0]["text"] == "Test"

    def test_save_creates_file(self, tmp_path: Path) -> None:
        segs = [TranscriptSegment(start=0, end=1, text="Hello")]
        writer = TranscriptWriter(OutputFormat.MARKDOWN)
        out = writer.save(_make_result(segs), tmp_path / "out")
        assert out.exists()
        assert out.suffix == ".md"
        assert "Hello" in out.read_text()

    def test_save_json_extension(self, tmp_path: Path) -> None:
        writer = TranscriptWriter(OutputFormat.JSON)
        out = writer.save(_make_result(), tmp_path / "out")
        assert out.suffix == ".json"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        writer = TranscriptWriter(OutputFormat.MARKDOWN)
        nested = tmp_path / "deep" / "nested" / "out"
        out = writer.save(_make_result(), nested)
        assert out.exists()
