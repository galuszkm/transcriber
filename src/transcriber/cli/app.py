"""CLI application entry point.

Wires together argument parsing, environment init, the transcription
pipeline, and Rich terminal output into a single :func:`main` function.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn

from .. import __version__
from ..core.config import TranscriptionConfig
from ..io.writer import OutputFormat, TranscriptWriter
from ..pipeline.transcriber import TranscriptionPipeline
from .display import console, print_banner, print_error, print_summary
from .parser import build_parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Meeting-Noter.

    Parses arguments, initialises the environment, runs the
    transcription pipeline, and writes the result to disk.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code - ``0`` on success, ``1`` on error.
    """
    args = build_parser(__version__).parse_args(argv)

    config = _config_from_args(args)
    audio_path: Path = args.audio_file
    output_path: Path = args.output or audio_path.with_suffix("")
    fmt = OutputFormat(args.format)

    print_banner(audio_path, config, fmt.value)

    pipeline = TranscriptionPipeline(config)
    writer = TranscriptWriter(fmt)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Transcribing audio...", total=None)

        try:
            result = pipeline.run(audio_path)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            progress.stop()
            print_error(str(exc))
            return 1

        progress.update(task, description="Saving transcript...")
        saved_path = writer.save(result, output_path)

    print_summary(result, saved_path, config)
    return 0


def _config_from_args(args: object) -> TranscriptionConfig:
    """Build a :class:`TranscriptionConfig` from parsed CLI arguments.

    Args:
        args: Namespace returned by ``argparse.parse_args()``.

    Returns:
        Validated transcription configuration.
    """
    return TranscriptionConfig(
        model_size=args.model,  # type: ignore[attr-defined]
        device=args.device,  # type: ignore[attr-defined]
        compute_type=args.compute_type,  # type: ignore[attr-defined]
        language=args.language,  # type: ignore[attr-defined]
        batch_size=args.batch_size,  # type: ignore[attr-defined]
        diarize=args.diarize,  # type: ignore[attr-defined]
        hf_token=args.hf_token,  # type: ignore[attr-defined]
    )


if __name__ == "__main__":
    sys.exit(main())
