"""WhisperX transcription pipeline orchestrator.

Provides :class:`TranscriptionPipeline`, the main entry point that
chains audio loading, model inference, and (when diarization is enabled)
alignment and speaker diarization into a single
:meth:`~TranscriptionPipeline.run` call.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from ..core.config import TranscriptionConfig
from ..core.models import TranscriptResult, TranscriptSegment
from ..io.audio import load_audio
from .alignment import align_segments
from .diarization import diarize_segments, load_diarization_pipeline

logger = logging.getLogger(__name__)

_STEP_LABELS: dict[str, str] = {
    "audio_load": "Loading audio",
    "model_load": "Loading Whisper model",
    "diarization_load": "Loading diarization model",
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
        self._diarization_model: Any = None
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

    def run(
        self,
        audio_path: Path,
        *,
        progress_fn: Callable[[str, str], None] | None = None,
    ) -> TranscriptResult:
        """Execute the full transcription pipeline.

        Steps:
            1. Load and decode audio to 16 kHz float32.
            2. Load Whisper model (lazy, cached after first call).
            3. Run batch transcription.
            4. Align word-level timestamps and diarize speakers (when diarization is enabled).
            5. Assemble typed result.

        Args:
            audio_path: Path to the audio file.
            progress_fn: Optional callback ``(stage, message)`` invoked
                before each pipeline step.

        Returns:
            Typed :class:`TranscriptResult` with segments and timings.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            ValueError: If the audio format is unsupported.
            RuntimeError: If transcription fails.
        """
        self._timings.clear()
        audio = self._timed(
            "audio_load", load_audio, audio_path, progress_fn=progress_fn
        )
        return self._run_pipeline(
            audio, source_label=str(audio_path), progress_fn=progress_fn
        )

    def run_from_audio(
        self,
        audio: np.ndarray,
        *,
        source_label: str = "<stream>",
        diarize: bool | None = None,
        progress_fn: Callable[[str, str], None] | None = None,
    ) -> TranscriptResult:
        """Execute the pipeline on a pre-decoded audio array.

        Useful when audio is received over the network and already
        decoded to a 16 kHz float32 NumPy array.

        Args:
            audio: 1-D float32 audio array at 16 kHz.
            source_label: Label for the source (used in result metadata).
            diarize: Per-call override for speaker diarization.
                ``None`` falls back to ``self._config.diarize``.
            progress_fn: Optional callback ``(stage, message)`` invoked
                before each pipeline step.

        Returns:
            Typed :class:`TranscriptResult` with segments and timings.
        """
        self._timings.clear()
        return self._run_pipeline(
            audio, source_label=source_label, diarize=diarize, progress_fn=progress_fn
        )

    def ensure_ready(self) -> None:
        """Eagerly load all models so they are warm for the first request."""
        self._ensure_model()
        if self._config.hf_token:
            self._ensure_diarization_model()

    # -- pipeline core -----------------------------------------------------

    def _run_pipeline(
        self,
        audio: np.ndarray,
        source_label: str,
        diarize: bool | None = None,
        progress_fn: Callable[[str, str], None] | None = None,
    ) -> TranscriptResult:
        """Shared pipeline logic used by both :meth:`run` and :meth:`run_from_audio`."""
        self._ensure_model()
        raw = self._timed(
            "transcribe", self._transcribe, audio, progress_fn=progress_fn
        )
        language = _detect_language(raw)

        should_diarize = self._config.diarize if diarize is None else diarize

        if should_diarize and not self._config.hf_token:
            msg = (
                "Speaker diarization requires a HuggingFace token. "
                "Set HF_TOKEN in .env and restart the server."
            )
            raise ValueError(msg)

        # Alignment is only needed for diarization.
        if should_diarize:
            self._ensure_diarization_model()
            segments = self._timed(
                "align",
                align_segments,
                audio,
                raw["segments"],
                language,
                self._config.device,
                progress_fn=progress_fn,
            )
            segments = self._timed(
                "diarize",
                diarize_segments,
                audio,
                segments,
                pipeline=self._diarization_model,
                progress_fn=progress_fn,
            )
        else:
            segments = raw["segments"]

        return self._assemble(source_label, language, segments)

    # -- model management --------------------------------------------------

    def _ensure_model(self) -> None:
        """Load the WhisperX model if not already cached."""
        if self._model is not None:
            return

        try:
            self._model = self._timed("model_load", self._load_model)
        except ValueError as exc:
            self._model = self._fallback_float32(exc)

    def _ensure_diarization_model(self) -> None:
        """Load the diarization pipeline if not already cached."""
        if self._diarization_model is not None:
            return
        self._diarization_model = self._timed(
            "diarization_load",
            load_diarization_pipeline,
            self._config.hf_token,
            self._config.device,
            self._config.cache_dir,
        )

    def _load_model(self) -> Any:
        """Load the WhisperX model from the current config.

        Returns:
            Loaded WhisperX model instance.
        """
        import whisperx

        return whisperx.load_model(
            self._config.model,
            device=self._config.device,
            compute_type=self._config.compute_type,
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

        self._config = self._config.with_overrides(compute_type="float32")
        import whisperx

        return whisperx.load_model(
            self._config.model,
            device=self._config.device,
            compute_type="float32",
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
        try:
            return self._model.transcribe(audio, batch_size=self._config.batch_size)
        except Exception as exc:
            msg = f"Transcription failed: {exc}"
            raise RuntimeError(msg) from exc

    # -- result assembly ---------------------------------------------------

    def _assemble(
        self,
        source_label: str,
        language: str,
        segments_data: list[dict[str, Any]],
    ) -> TranscriptResult:
        """Build the final :class:`TranscriptResult`.

        Args:
            source_label: Label for the audio source (file path or tag).
            language: Detected or configured language code.
            segments_data: Raw segment dicts after all processing.

        Returns:
            Typed Pydantic result model.
        """
        segments = build_segments(segments_data)
        duration = segments[-1].end if segments else 0.0

        return TranscriptResult(
            source_file=source_label,
            language=language,
            segments=segments,
            duration=duration,
            timings=self._timings,
        )

    # -- timing helper -----------------------------------------------------

    def _timed(
        self,
        label: str,
        fn: Any,
        *args: Any,
        progress_fn: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Call *fn* and record wall-clock duration under *label*.

        Args:
            label: Key for the timings dict.
            fn: Callable to invoke.
            *args: Positional arguments forwarded to *fn*.
            progress_fn: Optional callback ``(stage, message)`` invoked
                before the step starts.
            **kwargs: Keyword arguments forwarded to *fn*.

        Returns:
            Whatever *fn* returns.
        """
        name = _STEP_LABELS.get(label, label)
        if progress_fn is not None:
            progress_fn(label, name)
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


def _detect_language(raw_result: dict[str, Any]) -> str:
    """Extract the detected language from a raw WhisperX result.

    Args:
        raw_result: Dict returned by ``model.transcribe()``.

    Returns:
        ISO language code string.
    """
    return raw_result.get("language", "unknown")


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
