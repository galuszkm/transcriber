"""Configuration for the transcription pipeline.

Provides :class:`TranscriptionConfig`, a frozen Pydantic Settings model
that controls WhisperX model loading, device selection, and inference
parameters.  Reads ``HF_TOKEN`` from the environment or a ``.env``
file in the current working directory.

Also defines the set of supported audio formats and valid Whisper model
sizes.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .._env import cache_dir as _default_cache_dir

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
# Config
# ---------------------------------------------------------------------------


class TranscriptionConfig(BaseSettings):
    """Immutable configuration for the WhisperX transcription pipeline.

    Reads from environment variables (``MODEL``, ``DEVICE``,
    ``DIARIZE``, ``CACHE_DIR``, ``HF_TOKEN``) and the ``.env`` file
    in the current working directory.  CLI arguments take highest
    priority, then env vars, then defaults.

    Language is always auto-detected from the audio.

    Attributes:
        model: Whisper model size identifier.
        device: Compute device — ``"cuda"`` or ``"cpu"``.
        compute_type: Inference precision — ``"float16"``, ``"int8"``,
            ``"float32"``, or ``"auto"`` (resolved at init time).
        batch_size: Batch size for transcription inference.
        diarize: Whether to run speaker diarization.
        hf_token: HuggingFace token for pyannote diarization models.
        cache_dir: Root directory for model and data caches.
            Defaults to ``CACHE_DIR`` env var, then ``<cwd>/.cache``.
    """

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "auto"
    batch_size: int = 16
    diarize: bool = False
    hf_token: str | None = None
    cache_dir: Path | None = None
    # -- validators --------------------------------------------------------

    @field_validator("model")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if v not in VALID_MODEL_SIZES:
            msg = (
                f"Invalid model size '{v}'. "
                f"Must be one of: {', '.join(sorted(VALID_MODEL_SIZES))}"
            )
            raise ValueError(msg)
        return v

    @field_validator("device")
    @classmethod
    def _check_device(cls, v: str) -> str:
        valid = {"cpu", "cuda"}
        if v not in valid:
            msg = f"Invalid device '{v}'. Must be one of: {', '.join(sorted(valid))}"
            raise ValueError(msg)
        return v

    @field_validator("compute_type")
    @classmethod
    def _check_compute_type(cls, v: str) -> str:
        valid = {"float16", "int8", "float32", "auto"}
        if v not in valid:
            msg = (
                f"Invalid compute type '{v}'. "
                f"Must be one of: {', '.join(sorted(valid))}"
            )
            raise ValueError(msg)
        return v

    @field_validator("batch_size")
    @classmethod
    def _check_batch_size(cls, v: int) -> int:
        if v < 1:
            msg = f"Batch size must be >= 1, got {v}"
            raise ValueError(msg)
        return v

    @model_validator(mode="before")
    @classmethod
    def _resolve_computed_defaults(cls, values: dict) -> dict:
        """Resolve ``compute_type="auto"`` and ``cache_dir=None``."""
        if values.get("compute_type", "auto") == "auto":
            values["compute_type"] = _resolve_compute_type(
                values.get("device", "cuda"),
            )
        # Resolve cache_dir to the default when not provided.
        if values.get("cache_dir") is None:
            values["cache_dir"] = _default_cache_dir()
        return values

    @model_validator(mode="after")
    def _check_diarization_token(self) -> TranscriptionConfig:
        """Ensure a HuggingFace token is available when diarization is on."""
        if self.diarize and not self.hf_token:
            msg = (
                "Speaker diarization requires a HuggingFace token. "
                "Set HF_TOKEN env variable or pass --hf-token."
            )
            raise ValueError(msg)
        return self

    # -- factories ---------------------------------------------------------

    def with_overrides(self, **kwargs: object) -> TranscriptionConfig:
        """Return a new config with selected fields replaced.

        Because the config is frozen, this is the canonical way to
        derive a modified configuration (e.g. falling back from
        ``float16`` to ``float32``).

        Args:
            **kwargs: Field names and their replacement values.

        Returns:
            New :class:`TranscriptionConfig` instance.
        """
        current = self.model_dump()
        current.update(kwargs)
        return TranscriptionConfig(**current)


class CacheConfig(BaseSettings):
    """Configuration for ``trans-cache``.

    Reads the same environment variables as
    :class:`TranscriptionConfig` (``MODEL``, ``LANGUAGE``, ``DEVICE``,
    ``DIARIZE``, ``CACHE_DIR``, ``HF_TOKEN``) from the environment or
    ``.env`` file.  CLI arguments take highest priority, then env
    vars, then defaults.

    For the cache command, ``model`` and ``language`` accept
    comma-separated values to cache multiple models/languages at once.
    When ``language`` is empty (the default), **all** languages with
    known alignment models are cached.

    Attributes:
        model: Comma-separated Whisper model sizes to cache.
        language: Comma-separated ISO language codes (empty = all).
        device: Device for model loading during download.
        diarize: Whether to download diarization models.
        hf_token: HuggingFace token (shared with transcription config).
        cache_dir: Root cache directory.
    """

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model: str = "large-v3"
    language: str = ""
    device: str = "cpu"
    diarize: bool = False
    hf_token: str | None = None
    cache_dir: Path | None = None

    @field_validator("model")
    @classmethod
    def _check_cache_models(cls, v: str) -> str:
        items = [x.strip() for x in v.split(",") if x.strip()]
        invalid = set(items) - VALID_MODEL_SIZES
        if invalid:
            msg = (
                f"Invalid model sizes: {', '.join(sorted(invalid))}. "
                f"Valid: {', '.join(sorted(VALID_MODEL_SIZES))}"
            )
            raise ValueError(msg)
        return v

    @field_validator("device")
    @classmethod
    def _check_cache_device(cls, v: str) -> str:
        valid = {"cpu", "cuda"}
        if v not in valid:
            msg = f"Invalid device '{v}'. Must be one of: {', '.join(sorted(valid))}"
            raise ValueError(msg)
        return v

    @model_validator(mode="before")
    @classmethod
    def _resolve_cache_defaults(cls, values: dict) -> dict:
        if values.get("cache_dir") is None:
            values["cache_dir"] = _default_cache_dir()
        return values

    @property
    def models(self) -> list[str]:
        """Parsed list of Whisper model sizes."""
        return [x.strip() for x in self.model.split(",") if x.strip()]

    @property
    def languages(self) -> list[str]:
        """Parsed list of language codes (empty string → all available)."""
        if not self.language.strip():
            return []  # caller resolves to all available
        return [x.strip() for x in self.language.split(",") if x.strip()]
