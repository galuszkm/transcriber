"""Speaker diarization and re-segmentation.

Wraps the pyannote-based diarization pipeline provided by WhisperX
and applies a word-level re-segmentation pass so that each output
segment belongs to exactly one speaker.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def diarize_segments(
    audio: np.ndarray,
    segments: list[dict[str, Any]],
    *,
    hf_token: str,
    device: str,
) -> list[dict[str, Any]]:
    """Run speaker diarization and re-segment by speaker.

    1. Run the pyannote diarization pipeline.
    2. Assign speakers at the word level via WhisperX.
    3. Re-segment at every speaker change boundary.

    Falls back to the original *segments* on failure.

    Args:
        audio: 16 kHz float32 audio array.
        segments: Aligned transcription segments.
        hf_token: HuggingFace authentication token.
        device: Compute device (``"cuda"`` or ``"cpu"``).

    Returns:
        Segments with per-speaker labels.
    """
    try:
        return _run_diarization(audio, segments, hf_token=hf_token, device=device)
    except Exception:
        logger.error(
            "Diarization failed - returning undiarized segments",
            exc_info=True,
        )
        return segments


def _run_diarization(
    audio: np.ndarray,
    segments: list[dict[str, Any]],
    *,
    hf_token: str,
    device: str,
) -> list[dict[str, Any]]:
    """Execute the full diarization pipeline.

    Args:
        audio: 16 kHz float32 audio array.
        segments: Aligned transcription segments.
        hf_token: HuggingFace authentication token.
        device: Compute device string.

    Returns:
        Re-segmented segment list.
    """
    import whisperx
    from whisperx.diarize import DiarizationPipeline

    cache_dir = Path(__file__).parents[3] / ".cache" / "whisperx"
    pipeline = DiarizationPipeline(token=hf_token, device=device, cache_dir=cache_dir)
    diarize_segments = pipeline(audio)

    assigned = whisperx.assign_word_speakers(
        diarize_segments, {"segments": segments}
    ).get("segments", segments)

    return resegment_by_speaker(assigned)


# ---------------------------------------------------------------------------
# Re-segmentation (pure functions)
# ---------------------------------------------------------------------------


def resegment_by_speaker(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Re-segment transcription at speaker-change boundaries.

    WhisperX's ``assign_word_speakers`` labels each original segment
    with a *single* speaker via majority vote.  This function walks
    word-level data and creates a new segment at every speaker change
    so each output segment belongs to exactly one speaker.

    Args:
        segments: Segments with word-level ``speaker`` annotations.

    Returns:
        New list of segments split at speaker boundaries.
    """
    result: list[dict[str, Any]] = []
    for seg in segments:
        result.extend(_split_segment(seg))
    return result


def _split_segment(segment: dict[str, Any]) -> list[dict[str, Any]]:
    """Split a single segment into sub-segments at speaker boundaries.

    If the segment lacks word-level speaker info it is returned as-is.

    Args:
        segment: Transcription segment dict with optional ``words``.

    Returns:
        One or more segment dicts, each with a single speaker.
    """
    words: list[dict[str, Any]] = segment.get("words", [])

    if not words or not any("speaker" in w for w in words):
        return [segment]

    groups = _group_words_by_speaker(words, segment.get("start", 0.0))
    return [seg for g in groups if (seg := _word_group_to_segment(g)) is not None]


def _group_words_by_speaker(
    words: list[dict[str, Any]],
    initial_start: float,
) -> list[dict[str, Any]]:
    """Group consecutive words sharing the same speaker label.

    Args:
        words: Word-level dicts with ``speaker`` and ``word`` keys.
        initial_start: Fallback start time for the first group.

    Returns:
        List of group dicts (``speaker``, ``start``, ``words``).
    """
    groups: list[dict[str, Any]] = []
    current_speaker: str | None = None
    current_words: list[dict[str, Any]] = []
    current_start: float = initial_start

    for word in words:
        speaker = word.get("speaker", current_speaker)

        if current_speaker is not None and speaker != current_speaker:
            groups.append(
                {
                    "speaker": current_speaker,
                    "start": current_start,
                    "words": list(current_words),
                }
            )
            current_words = []
            current_start = word.get("start", current_start)

        current_speaker = speaker
        current_words.append(word)

    if current_words:
        groups.append(
            {
                "speaker": current_speaker,
                "start": current_start,
                "words": list(current_words),
            }
        )

    return groups


def _word_group_to_segment(group: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a word group into a segment dict.

    Args:
        group: Dict with ``speaker``, ``start``, and ``words`` keys.

    Returns:
        Segment dict, or ``None`` when the group text is empty.
    """
    words: list[dict[str, Any]] = group["words"]
    text = " ".join(w.get("word", "") for w in words).strip()

    if not text:
        return None

    return {
        "start": group["start"],
        "end": words[-1].get("end", group["start"]),
        "text": text,
        "speaker": group["speaker"],
        "words": words,
    }
