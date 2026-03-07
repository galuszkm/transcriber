"""Core data structures and configuration.

Re-exports the central configuration dataclass and Pydantic models
used throughout the package.
"""

from .config import (
    SUPPORTED_AUDIO_FORMATS,
    VALID_MODEL_SIZES,
    CacheConfig,
    TranscriptionConfig,
)
from .models import TranscriptResult, TranscriptSegment

__all__ = [
    "SUPPORTED_AUDIO_FORMATS",
    "VALID_MODEL_SIZES",
    "CacheConfig",
    "TranscriptResult",
    "TranscriptSegment",
    "TranscriptionConfig",
]
