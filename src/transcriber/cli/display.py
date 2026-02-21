"""Rich console display helpers.

Contains all terminal-output logic (banners, summaries, spinners)
so that ``cli.app`` stays focused on orchestration.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from ..core.config import TranscriptionConfig
from ..core.models import TranscriptResult

# Shared console instance used across the CLI layer.
console = Console()


def print_banner(
    audio_path: Path,
    config: TranscriptionConfig,
    fmt: str,
) -> None:
    """Print the startup information panel.

    Args:
        audio_path: Path to the input audio file.
        config: Active pipeline configuration.
        fmt: Chosen output format label.
    """
    console.print(
        Panel(
            f"[bold]Audio:[/]   {audio_path.name}\n"
            f"[bold]Model:[/]   {config.model_size}\n"
            f"[bold]Device:[/]  {config.device}\n"
            f"[bold]Format:[/]  {fmt}\n"
            f"[bold]Diarize:[/] {'yes' if config.diarize else 'no'}",
            title="Meeting-Noter",
            border_style="cyan",
        )
    )


def print_summary(
    result: TranscriptResult,
    saved_path: Path,
    config: TranscriptionConfig,
) -> None:
    """Print the post-transcription summary with timing breakdown.

    Args:
        result: Completed transcription result.
        saved_path: Path where the transcript was written.
        config: Active pipeline configuration.
    """
    console.print(f"\n[bold green]Done:[/] Transcript saved to: [cyan]{saved_path}[/]")
    console.print(f"  Language: {result.language}")
    console.print(f"  Segments: {len(result.segments)}")
    console.print(f"  Audio duration: {result.duration:.1f}s")

    console.print(f"  [dim]Speed:[/] {_format_timings(result.timings, config)}")


def print_error(message: str) -> None:
    """Print an error message in bold red.

    Args:
        message: Error description.
    """
    console.print(f"[bold red]Error:[/] {message}")


def _format_timings(
    timings: dict[str, float],
    config: TranscriptionConfig,
) -> str:
    """Build a human-readable timing breakdown string.

    Args:
        timings: Per-step wall-clock measurements.
        config: Pipeline config (to know if diarize was on).

    Returns:
        Pipe-separated timing summary.
    """
    parts = [
        f"Load {timings.get('model_load', 0):.1f}s",
        f"Transcribe {timings.get('transcribe', 0):.1f}s",
        f"Align {timings.get('align', 0):.1f}s",
    ]
    if config.diarize:
        parts.append(f"Diarize {timings.get('diarize', 0):.1f}s")
    return " | ".join(parts)
