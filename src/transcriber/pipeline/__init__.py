"""Transcription pipeline components.

Re-exports the main :class:`TranscriptionPipeline` orchestrator
and the convenience :func:`transcribe` wrapper.
"""

from .transcriber import TranscriptionPipeline, transcribe

__all__ = [
    "TranscriptionPipeline",
    "transcribe",
]
