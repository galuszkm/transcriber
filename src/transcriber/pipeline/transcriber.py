"""WhisperX transcription pipeline orchestrator.

Provides :class:`TranscriptionPipeline`, the main entry point that
chains audio loading, model inference, alignment, and diarization
into a single :meth:`~TranscriptionPipeline.run` call.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from ..core.config import TranscriptionConfig
from ..core.models import TranscriptResult, TranscriptSegment
from ..io.audio import load_audio
from .alignment import align_segments
from .diarization import diarize_segments

logger = logging.getLogger(__name__)

_STEP_LABELS: dict[str, str] = {
    "audio_load": "Loading audio",
    "model_load": "Loading Whisper model",
    "transcribe": "Transcribing speech",
    "align": "Aligning word timestamps",
    "diarize": "Diarizing speakers",
}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class TranscriptionPipeline:
    """End-to-end WhisperX transcription pipeline.

    The Whisper model is loaded lazily on the first :meth:`run` call
    and reused for subsequent invocations.

    Args:
        config: Pipeline configuration (model size, device, etc.).
    """

    def __init__(self, config: TranscriptionConfig) -> None:
        """Initialise the pipeline with the given configuration."""
        self._config = config
        self._model: Any = None
        self._timings: dict[str, float] = {}

    # -- public API --------------------------------------------------------

    @property
    def config(self) -> TranscriptionConfig:
        """Return the active pipeline configuration."""
        return self._config

    @property
    def timings(self) -> dict[str, float]:
        """Return a copy of the per-step timing measurements."""
        return dict(self._timings)

    def run(self, audio_path: Path) -> TranscriptResult:
        """Execute the full transcription pipeline.

        Steps:
            1. Load and decode audio to 16 kHz float32.
            2. Load Whisper model (lazy, cached after first call).
            3. Run batch transcription.
            4. Align word-level timestamps.
            5. Diarize speakers (when enabled).
            6. Assemble typed result.

        Args:
            audio_path: Path to the audio file.

        Returns:
            Typed :class:`TranscriptResult` with segments and timings.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            ValueError: If the audio format is unsupported.
            RuntimeError: If transcription fails.
        """
        self._timings.clear()

        audio = self._timed("audio_load", load_audio, audio_path)
        self._ensure_model()
        raw = self._transcribe(audio)
        language = _detect_language(raw, self._config.language)

        segments = self._timed(
            "align",
            align_segments,
            audio,
            raw["segments"],
            language,
            self._config.device,
        )

        if self._config.diarize and self._config.hf_token:
            segments = self._timed(
                "diarize",
                diarize_segments,
                audio,
                segments,
                hf_token=self._config.hf_token,
                device=self._config.device,
            )

        return self._assemble(audio_path, language, segments)

    # -- model management --------------------------------------------------

    def _ensure_model(self) -> None:
        """Load the WhisperX model if not already cached."""
        if self._model is not None:
            return

        try:
            self._model = self._timed("model_load", self._load_model)
        except ValueError as exc:
            self._model = self._fallback_float32(exc)

    def _load_model(self) -> Any:
        """Load the WhisperX model from the current config.

        Returns:
            Loaded WhisperX model instance.
        """
        import whisperx

        return whisperx.load_model(
            self._config.model_size,
            device=self._config.device,
            compute_type=self._config.compute_type,
            language=self._config.language,
        )

    def _fallback_float32(self, exc: ValueError) -> Any:
        """Retry model loading with float32 when float16 is unsupported.

        Args:
            exc: The original ``ValueError`` from model loading.

        Returns:
            Loaded WhisperX model with float32 precision.

        Raises:
            ValueError: Re-raised when the error is unrelated to float16.
        """
        if "float16" not in str(exc) or self._config.compute_type != "float16":
            raise

        logger.warning("float16 unsupported on this device - falling back to float32")

        self._config = TranscriptionConfig(
            model_size=self._config.model_size,
            device=self._config.device,
            compute_type="float32",
            language=self._config.language,
            batch_size=self._config.batch_size,
            diarize=self._config.diarize,
            hf_token=self._config.hf_token,
        )
        import whisperx

        return whisperx.load_model(
            self._config.model_size,
            device=self._config.device,
            compute_type="float32",
            language=self._config.language,
        )

    # -- inference ---------------------------------------------------------

    def _transcribe(self, audio: np.ndarray) -> dict[str, Any]:
        """Run WhisperX batch transcription.

        Args:
            audio: 16 kHz float32 audio array.

        Returns:
            Raw WhisperX result dict.

        Raises:
            RuntimeError: On transcription failure.
        """

        def _run() -> dict[str, Any]:
            try:
                return self._model.transcribe(audio, batch_size=self._config.batch_size)
            except Exception as exc:
                msg = f"Transcription failed: {exc}"
                raise RuntimeError(msg) from exc

        return self._timed("transcribe", _run)

    # -- result assembly ---------------------------------------------------

    def _assemble(
        self,
        audio_path: Path,
        language: str,
        segments_data: list[dict[str, Any]],
    ) -> TranscriptResult:
        """Build the final :class:`TranscriptResult`.

        Args:
            audio_path: Original audio file path.
            language: Detected or configured language code.
            segments_data: Raw segment dicts after all processing.

        Returns:
            Typed Pydantic result model.
        """
        segments = build_segments(segments_data)
        duration = segments[-1].end if segments else 0.0

        return TranscriptResult(
            source_file=str(audio_path),
            language=language,
            segments=segments,
            duration=duration,
            timings=self._timings,
        )

    # -- timing helper -----------------------------------------------------

    def _timed(self, label: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Call *fn* and record wall-clock duration under *label*.

        Args:
            label: Key for the timings dict.
            fn: Callable to invoke.
            *args: Positional arguments forwarded to *fn*.
            **kwargs: Keyword arguments forwarded to *fn*.

        Returns:
            Whatever *fn* returns.
        """
        name = _STEP_LABELS.get(label, label)
        logger.info("[pipeline] %-30s ...", name)
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        self._timings[label] = elapsed
        logger.info("[pipeline] %-30s done  (%.1fs)", name, elapsed)
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_segments(
    raw_segments: list[dict[str, Any]],
) -> list[TranscriptSegment]:
    """Convert raw WhisperX segment dicts to typed Pydantic models.

    Args:
        raw_segments: List of dicts from the WhisperX pipeline.

    Returns:
        Validated :class:`TranscriptSegment` instances.
    """
    return [
        TranscriptSegment(
            start=seg.get("start", 0.0),
            end=seg.get("end", 0.0),
            text=seg.get("text", ""),
            speaker=seg.get("speaker"),
            words=seg.get("words", []),
        )
        for seg in raw_segments
    ]


def _detect_language(
    raw_result: dict[str, Any],
    configured: str | None,
) -> str:
    """Extract the detected language from a raw WhisperX result.

    Args:
        raw_result: Dict returned by ``model.transcribe()``.
        configured: User-specified language (may be ``None``).

    Returns:
        ISO language code string.
    """
    return raw_result.get("language", configured or "unknown")


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------


def transcribe(
    audio_path: Path,
    config: TranscriptionConfig | None = None,
) -> TranscriptResult:
    """Transcribe an audio file (convenience one-shot wrapper).

    For repeated calls prefer :class:`TranscriptionPipeline` directly
    so the Whisper model is loaded only once.

    Args:
        audio_path: Path to the audio file.
        config: Optional configuration; uses defaults when ``None``.

    Returns:
        Typed transcription result.
    """
    pipeline = TranscriptionPipeline(config or TranscriptionConfig())
    return pipeline.run(audio_path)
