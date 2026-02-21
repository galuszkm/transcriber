"""Audio file loading and validation.

Validates input audio files (existence, format) and decodes them
to 16 kHz mono float32 NumPy arrays via PyAV — a production-grade
Python binding to FFmpeg's C libraries.
"""

from __future__ import annotations

from pathlib import Path

import av
import numpy as np

from ..core.config import SUPPORTED_AUDIO_FORMATS

#: Target sample rate expected by WhisperX.
SAMPLE_RATE: int = 16_000


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_audio_file(file_path: Path) -> Path:
    """Validate that the audio file exists and has a supported format.

    Args:
        file_path: Path to the audio file to validate.

    Returns:
        Resolved absolute path to the validated file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is not supported.
    """
    resolved = file_path.resolve()

    if not resolved.is_file():
        msg = f"Audio file not found: {resolved}"
        raise FileNotFoundError(msg)

    suffix = resolved.suffix.lower()
    if suffix not in SUPPORTED_AUDIO_FORMATS:
        msg = (
            f"Unsupported audio format '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_FORMATS))}"
        )
        raise ValueError(msg)

    return resolved


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_audio(file_path: Path) -> np.ndarray:
    """Load and decode an audio file to 16 kHz mono float32.

    Uses PyAV (FFmpeg C bindings) under the hood.  The returned array
    is the format WhisperX expects as input.

    Args:
        file_path: Path to the audio file.

    Returns:
        1-D ``float32`` NumPy array of audio samples at 16 kHz.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.
        RuntimeError: If audio decoding fails.
    """
    validated = validate_audio_file(file_path)
    return _decode_with_pyav(validated)


def _decode_with_pyav(path: Path) -> np.ndarray:
    """Decode *path* into a 16 kHz mono float32 array via PyAV.

    Args:
        path: Validated audio file path.

    Returns:
        Concatenated float32 audio samples.

    Raises:
        RuntimeError: On empty audio or decoding failure.
    """
    try:
        container = av.open(str(path))
        resampler = av.AudioResampler(
            format="fltp",
            layout="mono",
            rate=SAMPLE_RATE,
        )

        chunks: list[np.ndarray] = _extract_chunks(container, resampler)
        container.close()

        if not chunks:
            msg = f"No audio data decoded from '{path}'"
            raise RuntimeError(msg)

        return np.concatenate(chunks).astype(np.float32)

    except (RuntimeError, ValueError):
        raise
    except Exception as exc:
        msg = f"Failed to load audio from '{path}': {exc}"
        raise RuntimeError(msg) from exc


def _extract_chunks(
    container: av.container.InputContainer,
    resampler: av.AudioResampler,
) -> list[np.ndarray]:
    """Decode and resample all frames from *container*.

    Args:
        container: Open PyAV input container.
        resampler: Configured 16 kHz mono resampler.

    Returns:
        List of float32 NumPy chunk arrays.
    """
    chunks: list[np.ndarray] = []

    for frame in container.decode(audio=0):
        for out_frame in resampler.resample(frame):
            chunks.append(out_frame.to_ndarray()[0])

    # Flush resampler
    for out_frame in resampler.resample(None):
        chunks.append(out_frame.to_ndarray()[0])

    return chunks


# ---------------------------------------------------------------------------
# Audio splitting
# ---------------------------------------------------------------------------


def split_audio(
    audio: np.ndarray,
    chunk_duration_seconds: float = 600.0,
) -> list[np.ndarray]:
    """Split audio into chunks of specified duration.

    Useful when processing very large audio files that exceed GPU memory.
    Each chunk is independent and can be processed separately.

    Args:
        audio: 16 kHz float32 audio array.
        chunk_duration_seconds: Duration of each chunk in seconds (default 10 min).

    Returns:
        List of audio chunks as float32 NumPy arrays.

    Example:
        >>> chunks = split_audio(audio, chunk_duration_seconds=600)
        >>> for chunk in chunks:
        ...     result = pipeline.run(chunk)
    """
    if chunk_duration_seconds <= 0:
        msg = "chunk_duration_seconds must be positive"
        raise ValueError(msg)

    chunk_samples = int(chunk_duration_seconds * SAMPLE_RATE)
    chunks = []

    for i in range(0, len(audio), chunk_samples):
        chunk = audio[i : i + chunk_samples]
        if len(chunk) > 0:
            chunks.append(chunk.astype(np.float32))

    return chunks if chunks else [audio]
