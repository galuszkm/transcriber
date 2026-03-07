"""Audio I/O and transcript output.

Re-exports the audio loader/decoder and transcript writer.
"""

from .audio import (
    SAMPLE_RATE,
    decode_bytes,
    load_audio,
    split_audio,
    validate_audio_file,
)
from .writer import OutputFormat, TranscriptWriter

__all__ = [
    "SAMPLE_RATE",
    "OutputFormat",
    "TranscriptWriter",
    "decode_bytes",
    "load_audio",
    "split_audio",
    "validate_audio_file",
]
