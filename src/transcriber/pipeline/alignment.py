"""Word-level timestamp alignment.

Wraps the WhisperX phoneme alignment step, providing a clean
interface and graceful fallback when alignment is unavailable
for a given language.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def align_segments(
    audio: np.ndarray,
    raw_segments: list[dict[str, Any]],
    language: str,
    device: str,
) -> list[dict[str, Any]]:
    """Align word-level timestamps using a phoneme model.

    Falls back to the original unaligned segments when the alignment
    model is unavailable for *language* or when alignment fails for
    any other reason.

    Args:
        audio: 16 kHz float32 audio array.
        raw_segments: Segments produced by the transcription step.
        language: ISO language code.
        device: Compute device (``"cuda"`` or ``"cpu"``).

    Returns:
        Segments enriched with word-level timing data.
    """
    try:
        return _run_alignment(audio, raw_segments, language, device)
    except Exception:
        logger.warning("Alignment failed - using unaligned segments", exc_info=True)
        return raw_segments


def _run_alignment(
    audio: np.ndarray,
    raw_segments: list[dict[str, Any]],
    language: str,
    device: str,
) -> list[dict[str, Any]]:
    """Execute the WhisperX alignment pass.

    Args:
        audio: 16 kHz float32 audio array.
        raw_segments: Unaligned transcription segments.
        language: ISO language code for phoneme model selection.
        device: Compute device string.

    Returns:
        Aligned segments with word-level timing.
    """
    import whisperx

    align_model, metadata = whisperx.load_align_model(
        language_code=language,
        device=device,
    )
    aligned = whisperx.align(
        raw_segments,
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    return aligned.get("segments", raw_segments)
