"""Audio file loading, validation, and decoding.

Validates input audio files (existence, format) and decodes them
to 16 kHz mono float32 NumPy arrays via PyAV — a production-grade
Python binding to FFmpeg's C libraries.

The core decoding helpers (:func:`decode_stream`, :func:`decode_bytes`)
are also used by the server's in-memory audio decode path, keeping
the PyAV resampling logic in one place.
"""

from __future__ import annotations

import io
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
    try:
        return decode_stream(av.open(str(validated)), source=str(validated))
    except (RuntimeError, ValueError):
        raise
    except Exception as exc:
        msg = f"Failed to load audio from '{validated}': {exc}"
        raise RuntimeError(msg) from exc


# ---------------------------------------------------------------------------
# Core decoding (shared between file-based and in-memory paths)
# ---------------------------------------------------------------------------


def decode_stream(
    container: av.container.InputContainer,
    *,
    source: str = "<stream>",
) -> np.ndarray:
    """Decode an open PyAV container to a 16 kHz mono float32 array.

    This is the single implementation of the PyAV → NumPy decoding
    pipeline used by both the file-based :func:`load_audio` and the
    server's :func:`decode_bytes` paths.

    Args:
        container: Open PyAV input container.
        source: Human-readable label for error messages.

    Returns:
        1-D ``float32`` NumPy array of audio samples at 16 kHz.

    Raises:
        RuntimeError: If no audio data could be decoded.
    """
    resampler = av.AudioResampler(
        format="fltp",
        layout="mono",
        rate=SAMPLE_RATE,
    )

    chunks: list[np.ndarray] = []
    for frame in container.decode(audio=0):
        for out_frame in resampler.resample(frame):
            chunks.append(out_frame.to_ndarray()[0])

    # Flush resampler
    for out_frame in resampler.resample(None):
        chunks.append(out_frame.to_ndarray()[0])

    container.close()

    if not chunks:
        msg = f"No audio data decoded from '{source}'"
        raise RuntimeError(msg)

    return np.concatenate(chunks).astype(np.float32)


def decode_bytes(data: bytes) -> np.ndarray:
    """Decode raw audio bytes to a 16 kHz mono float32 array.

    Accepts any format that PyAV/FFmpeg can read (WAV, MP3, FLAC,
    OGG, etc.).  Used by the server for network-received audio.

    Args:
        data: Raw audio file bytes.

    Returns:
        1-D ``float32`` NumPy array at 16 kHz.

    Raises:
        ValueError: If no audio data could be decoded.
    """
    container = av.open(io.BytesIO(data), mode="r")
    try:
        return decode_stream(container, source="<bytes>")
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc


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
