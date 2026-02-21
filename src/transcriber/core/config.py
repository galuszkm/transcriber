"""Configuration for the transcription pipeline.

Provides :class:`TranscriptionConfig`, a frozen dataclass that
controls WhisperX model loading, device selection, and inference
parameters.  Also defines the set of supported audio formats and
valid Whisper model sizes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_AUDIO_FORMATS: frozenset[str] = frozenset(
    {
        ".wav",
        ".mp3",
        ".flac",
        ".ogg",
        ".m4a",
        ".wma",
        ".aac",
        ".mp4",
        ".webm",
    }
)
"""File extensions accepted as audio input."""

VALID_MODEL_SIZES: frozenset[str] = frozenset(
    {
        "tiny",
        "base",
        "small",
        "medium",
        "large-v2",
        "large-v3",
    }
)
"""WhisperX model size identifiers."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_compute_type(device: str) -> str:
    """Pick the best compute type for *device*.

    For CUDA devices, inspects the GPU compute capability and returns
    ``"float16"`` when capability >= 7.0.  Falls back to ``"float32"``
    for everything else.

    Args:
        device: Target compute device (``"cuda"`` or ``"cpu"``).

    Returns:
        Resolved compute type string.
    """
    if device != "cuda":
        return "float32"
    try:
        import torch

        if not torch.cuda.is_available():
            return "float32"
        major, _ = torch.cuda.get_device_capability()
        return "float16" if major >= 7 else "float32"
    except Exception:
        return "float32"


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptionConfig:
    """Immutable configuration for the WhisperX transcription pipeline.

    Attributes:
        model_size: Whisper model size identifier.
        device: Compute device — ``"cuda"`` or ``"cpu"``.
        compute_type: Inference precision — ``"float16"``, ``"int8"``,
            ``"float32"``, or ``"auto"`` (resolved at init time).
        language: ISO language code, or ``None`` for auto-detection.
        batch_size: Batch size for transcription inference.
        diarize: Whether to run speaker diarization.
        hf_token: HuggingFace token for pyannote diarization models.
    """

    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "auto"
    language: str | None = None
    batch_size: int = 16
    diarize: bool = False
    hf_token: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalise configuration values."""
        self._validate_model_size()
        self._validate_device()
        self._validate_compute_type()
        self._validate_batch_size()
        self._resolve_hf_token()

    # -- validation helpers ------------------------------------------------

    def _validate_model_size(self) -> None:
        """Raise if *model_size* is not in :data:`VALID_MODEL_SIZES`."""
        if self.model_size not in VALID_MODEL_SIZES:
            msg = (
                f"Invalid model size '{self.model_size}'. "
                f"Must be one of: {', '.join(sorted(VALID_MODEL_SIZES))}"
            )
            raise ValueError(msg)

    def _validate_device(self) -> None:
        """Raise if *device* is not ``cpu`` or ``cuda``."""
        valid = {"cpu", "cuda"}
        if self.device not in valid:
            msg = (
                f"Invalid device '{self.device}'. "
                f"Must be one of: {', '.join(sorted(valid))}"
            )
            raise ValueError(msg)

    def _validate_compute_type(self) -> None:
        """Validate *compute_type* and resolve ``"auto"``."""
        valid = {"float16", "int8", "float32", "auto"}
        if self.compute_type not in valid:
            msg = (
                f"Invalid compute type '{self.compute_type}'. "
                f"Must be one of: {', '.join(sorted(valid))}"
            )
            raise ValueError(msg)

        if self.compute_type == "auto":
            resolved = _resolve_compute_type(self.device)
            object.__setattr__(self, "compute_type", resolved)

    def _validate_batch_size(self) -> None:
        """Raise if *batch_size* is less than 1."""
        if self.batch_size < 1:
            msg = f"Batch size must be >= 1, got {self.batch_size}"
            raise ValueError(msg)

    def _resolve_hf_token(self) -> None:
        """Auto-load ``HF_TOKEN`` from the environment when diarization is on."""
        if not self.diarize or self.hf_token:
            return

        token = os.environ.get("HF_TOKEN")
        if not token:
            msg = (
                "Speaker diarization requires a HuggingFace token. "
                "Set HF_TOKEN env variable or pass --hf-token."
            )
            raise ValueError(msg)
        object.__setattr__(self, "hf_token", token)
