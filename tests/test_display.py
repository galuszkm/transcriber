"""Tests for transcriber.cli.display - terminal output helpers."""

from io import StringIO
from pathlib import Path

from rich.console import Console

from transcriber.cli.display import print_banner, print_error, print_summary
from transcriber.core.config import TranscriptionConfig
from transcriber.core.models import TranscriptResult, TranscriptSegment


def _capture_console(fn, *args, **kwargs) -> str:
    """Run fn with a captured Rich console and return printed text."""
    import transcriber.cli.display as disp

    original = disp.console
    buf = StringIO()
    disp.console = Console(file=buf, force_terminal=True, width=120)
    try:
        fn(*args, **kwargs)
    finally:
        disp.console = original
    return buf.getvalue()


class TestPrintBanner:
    """Startup panel rendering."""

    def test_contains_audio_filename(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        output = _capture_console(
            print_banner, Path("meeting.wav"), cfg, "md"
        )
        assert "meeting.wav" in output

    def test_contains_model_and_device(self) -> None:
        cfg = TranscriptionConfig(
            compute_type="float32", device="cpu", model="tiny"
        )
        output = _capture_console(print_banner, Path("a.wav"), cfg, "json")
        assert "tiny" in output
        assert "cpu" in output


class TestPrintError:
    """Error message rendering."""

    def test_error_message_printed(self) -> None:
        output = _capture_console(print_error, "Something failed")
        assert "Something failed" in output


class TestPrintSummary:
    """Post-transcription summary rendering."""

    def test_summary_shows_language_and_segments(self) -> None:
        result = TranscriptResult(
            source_file="test.wav",
            language="de",
            segments=[TranscriptSegment(start=0, end=5, text="Hallo")],
            duration=5.0,
            timings={"transcribe": 2.0},
        )
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        output = _capture_console(
            print_summary, result, Path("/out/test.md"), cfg
        )
        assert "de" in output
        assert "1" in output  # 1 segment
