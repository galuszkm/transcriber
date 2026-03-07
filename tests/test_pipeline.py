"""Tests for transcriber.pipeline.transcriber - pipeline and helper methods."""

from unittest.mock import MagicMock, patch

import numpy as np

from transcriber.core.config import TranscriptionConfig
from transcriber.core.models import TranscriptResult
from transcriber.pipeline.transcriber import TranscriptionPipeline


class TestTranscriptionPipelineInit:
    """Pipeline construction and property access."""

    def test_config_property(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        assert pipeline.config is cfg

    def test_timings_initially_empty(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        assert pipeline.timings == {}


class TestAssemble:
    """Result assembly from raw segments."""

    def test_assembles_result(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        raw = [
            {"start": 0.0, "end": 2.5, "text": "Hello"},
            {"start": 2.5, "end": 5.0, "text": "world"},
        ]
        result = pipeline._assemble("test.wav", "en", raw)
        assert isinstance(result, TranscriptResult)
        assert result.source_file == "test.wav"
        assert result.language == "en"
        assert len(result.segments) == 2
        assert result.duration == 5.0

    def test_empty_segments_zero_duration(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        result = pipeline._assemble("test.wav", "en", [])
        assert result.duration == 0.0


class TestTimed:
    """_timed helper measures wall-clock time and calls progress_fn."""

    def test_records_timing(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        result = pipeline._timed("test_step", lambda: 42)
        assert result == 42
        assert "test_step" in pipeline.timings
        assert pipeline.timings["test_step"] >= 0

    def test_calls_progress_fn(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        calls = []
        pipeline._timed(
            "transcribe",
            lambda: None,
            progress_fn=lambda s, m: calls.append((s, m)),
        )
        assert len(calls) == 1
        assert calls[0][0] == "transcribe"

    def test_forwards_args(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        result = pipeline._timed("add", lambda a, b: a + b, 3, 4)
        assert result == 7


class TestEnsureModel:
    """Lazy model loading with float32 fallback."""

    def test_loads_model_once(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        mock_model = MagicMock()
        with patch.object(pipeline, "_load_model", return_value=mock_model):
            pipeline._ensure_model()
            assert pipeline._model is mock_model
            # Second call doesn't reload
            pipeline._ensure_model()

    def test_float16_fallback(self) -> None:
        cfg = TranscriptionConfig(compute_type="float16", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        fallback_model = MagicMock()
        mock_wx = MagicMock()
        mock_wx.load_model.return_value = fallback_model
        with (
            patch.object(
                pipeline,
                "_load_model",
                side_effect=ValueError("float16 is not supported"),
            ),
            patch.dict("sys.modules", {"whisperx": mock_wx}),
        ):
            pipeline._ensure_model()
            assert pipeline._model is fallback_model
            assert pipeline.config.compute_type == "float32"

    def test_non_float16_error_reraises(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)
        with patch.object(
            pipeline,
            "_load_model",
            side_effect=ValueError("some other error"),
        ):
            import pytest

            with pytest.raises(ValueError, match="some other error"):
                pipeline._ensure_model()


class TestRunFromAudio:
    """run_from_audio with a mocked pipeline."""

    def test_basic_run_without_diarize(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32", device="cpu")
        pipeline = TranscriptionPipeline(cfg)

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "segments": [{"start": 0, "end": 1, "text": "Hi"}],
            "language": "en",
        }
        pipeline._model = mock_model

        audio = np.zeros(16000, dtype=np.float32)
        result = pipeline.run_from_audio(audio, source_label="test")
        assert isinstance(result, TranscriptResult)
        assert result.language == "en"
        assert len(result.segments) == 1

    def test_diarize_requires_token(self) -> None:
        cfg = TranscriptionConfig(
            compute_type="float32", device="cpu", hf_token="", diarize=False
        )
        pipeline = TranscriptionPipeline(cfg)

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "segments": [],
            "language": "en",
        }
        pipeline._model = mock_model

        import pytest

        audio = np.zeros(16000, dtype=np.float32)
        with pytest.raises(ValueError, match="HuggingFace token"):
            pipeline.run_from_audio(audio, diarize=True)
