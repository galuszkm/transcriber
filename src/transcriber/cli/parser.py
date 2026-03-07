"""CLI argument parser definition.

Builds the ``argparse.ArgumentParser`` for the ``transcriber``
command and provides :func:`add_pipeline_args` to register the
shared model/device/precision arguments used by both the CLI
and the server entry points.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core.config import VALID_MODEL_SIZES
from ..io.writer import OutputFormat


def add_pipeline_args(
    parser: argparse.ArgumentParser,
    *,
    default_device: str = "cuda",
) -> None:
    """Add pipeline configuration arguments shared by CLI and server.

    Args:
        parser: Parser (or sub-parser) to extend.
        default_device: Default value for ``--device``
            (``"cuda"`` for both CLI and server).
    """
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="large-v3",
        choices=sorted(VALID_MODEL_SIZES),
        help="WhisperX model size (default: large-v3).",
    )
    parser.add_argument(
        "-d",
        "--device",
        type=str,
        default=default_device,
        choices=["cpu", "cuda"],
        help=f"Compute device (default: {default_device}).",
    )
    parser.add_argument(
        "-c",
        "--compute-type",
        type=str,
        default="auto",
        choices=["float16", "int8", "float32", "auto"],
        help="Compute precision (default: auto).",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=16,
        help="Inference batch size (default: 16).",
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        default=None,
        help="HuggingFace token for diarization (overrides HF_TOKEN env var).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=(
            "Root directory for model and data caches "
            "(default: TRANSCRIBER_CACHE_DIR env var, then <cwd>/.cache)."
        ),
    )


def build_parser(version: str) -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    Args:
        version: Version string shown by ``--version``.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="trans-cli",
        description="Transcribe meeting audio files using WhisperX.",
    )
    parser.add_argument(
        "audio_file",
        type=Path,
        help="Path to the audio file to transcribe.",
    )

    add_pipeline_args(parser, default_device="cuda")

    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default="md",
        choices=[f.value for f in OutputFormat],
        help="Output format (default: md).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path without extension (defaults to input filename).",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        default=False,
        help="Enable speaker diarization (requires HF_TOKEN).",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {version}",
    )
    return parser
