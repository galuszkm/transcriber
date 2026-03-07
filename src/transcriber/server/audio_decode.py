"""In-memory audio decoding for network-received bytes.

Thin wrappers around :func:`~transcriber.io.audio.decode_bytes`
that also handle base64 decoding.  All PyAV logic lives in
:mod:`transcriber.io.audio` so there is one decoding implementation.
"""

from __future__ import annotations

import base64

import numpy as np

from ..io.audio import decode_bytes as decode_audio_bytes


def decode_base64_audio(b64_string: str) -> np.ndarray:
    """Decode a base64-encoded audio string to a 16 kHz mono float32 array.

    Args:
        b64_string: Base64-encoded audio file data.

    Returns:
        1-D float32 NumPy array at 16 kHz.
    """
    raw = base64.b64decode(b64_string)
    return decode_audio_bytes(raw)
