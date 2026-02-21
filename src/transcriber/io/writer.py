"""Transcript formatting and file output.

Provides :class:`TranscriptWriter` for rendering transcription results
as Markdown or JSON and persisting them to disk, and :class:`OutputFormat`
for enumerating supported formats.
"""

from __future__ import annotations

import enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.models import TranscriptResult


# ---------------------------------------------------------------------------
# Format enum
# ---------------------------------------------------------------------------


class OutputFormat(enum.Enum):
    """Supported transcript output formats.

    Each member's *value* is the short name used by the CLI (``md``,
    ``json``).
    """

    MARKDOWN = "md"
    JSON = "json"

    @property
    def extension(self) -> str:
        """File extension with leading dot (e.g. ``.md``)."""
        return f".{self.value}"


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


class TranscriptWriter:
    """Renders and persists transcription results.

    Args:
        fmt: Desired output format (default: Markdown).
    """

    def __init__(self, fmt: OutputFormat = OutputFormat.MARKDOWN) -> None:
        """Initialise the writer with the desired output format."""
        self._fmt = fmt
        self._renderers = {
            OutputFormat.MARKDOWN: _render_markdown,
            OutputFormat.JSON: _render_json,
        }

    # -- public API --------------------------------------------------------

    def render(self, result: TranscriptResult) -> str:
        """Render the transcript as a string.

        Args:
            result: Transcription result to render.

        Returns:
            Formatted string (Markdown or JSON).
        """
        return self._renderers[self._fmt](result)

    def save(self, result: TranscriptResult, output_path: Path) -> Path:
        """Write the formatted transcript to disk.

        Creates parent directories when necessary.

        Args:
            result: Transcription result to save.
            output_path: Destination path **without** extension.

        Returns:
            Final path (with extension) of the written file.
        """
        content = self.render(result)
        final_path = output_path.with_suffix(self._fmt.extension)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text(content, encoding="utf-8")
        return final_path


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _render_markdown(result: TranscriptResult) -> str:
    """Render transcript as Markdown with speaker grouping.

    Consecutive segments by the same speaker are merged into a
    single block, ideal for LLM summarisation.

    Args:
        result: Transcription result.

    Returns:
        Complete Markdown document string.
    """
    lines = _markdown_header(result)

    if not result.segments:
        lines.append("*No speech detected.*")
        return "\n".join(lines)

    lines.extend(_markdown_speaker_blocks(result))
    return "\n".join(lines)


def _render_json(result: TranscriptResult) -> str:
    """Render transcript as pretty-printed JSON.

    Args:
        result: Transcription result.

    Returns:
        JSON string with 2-space indentation.
    """
    return result.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def _markdown_header(result: TranscriptResult) -> list[str]:
    """Build the Markdown preamble: title, metadata, separator.

    Args:
        result: Transcription result.

    Returns:
        List of Markdown lines.
    """
    return [
        f"# Transcript: {Path(result.source_file).stem}",
        "",
        f"**Language:** {result.language}  ",
        f"**Duration:** {format_timestamp(result.duration)}",
        "",
        "---",
        "",
    ]


def _markdown_speaker_blocks(result: TranscriptResult) -> list[str]:
    """Render speaker-grouped segments as Markdown blocks.

    Args:
        result: Transcription result containing segments.

    Returns:
        List of Markdown lines.
    """
    lines: list[str] = []
    current_speaker: str | None = None

    for seg in result.segments:
        speaker = seg.speaker or "Speaker"

        if speaker != current_speaker:
            current_speaker = speaker
            time_range = f"{format_timestamp(seg.start)} - {format_timestamp(seg.end)}"
            lines.append("")
            lines.append(f"**{speaker}** ({time_range}):  ")

        lines.append(seg.text.strip())

    return lines


# ---------------------------------------------------------------------------
# Timestamp formatting
# ---------------------------------------------------------------------------


def format_timestamp(seconds: float) -> str:
    """Format a duration in seconds as ``MM:SS`` or ``H:MM:SS``.

    Args:
        seconds: Non-negative duration value.

    Returns:
        Human-readable timestamp string.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
