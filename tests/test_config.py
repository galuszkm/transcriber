"""Tests for transcriber.core.config - validation and resolution logic."""

from pathlib import Path
from unittest.mock import patch

import pytest

from transcriber.core.config import (
    CacheConfig,
    TranscriptionConfig,
    _resolve_compute_type,
)

# ---------------------------------------------------------------------------
# _resolve_compute_type
# ---------------------------------------------------------------------------


class TestResolveComputeType:
    """Compute type auto-resolution for different devices."""

    def test_cpu_always_float32(self) -> None:
        assert _resolve_compute_type("cpu") == "float32"

    def test_cuda_no_torch_returns_float32(self) -> None:
        with patch.dict("sys.modules", {"torch": None}):
            assert _resolve_compute_type("cuda") == "float32"

    def test_cuda_not_available_returns_float32(self) -> None:
        mock_torch = type(
            "MockTorch",
            (),
            {"cuda": type("C", (), {"is_available": staticmethod(lambda: False)})()},
        )()
        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert _resolve_compute_type("cuda") == "float32"


# ---------------------------------------------------------------------------
# TranscriptionConfig validators
# ---------------------------------------------------------------------------


class TestTranscriptionConfigValidation:
    """Field and model validators on TranscriptionConfig."""

    def test_invalid_model_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid model size"):
            TranscriptionConfig(model="nonexistent", compute_type="float32")

    def test_invalid_device_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid device"):
            TranscriptionConfig(device="tpu", compute_type="float32")

    def test_invalid_compute_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid compute type"):
            TranscriptionConfig(compute_type="bfloat16")

    def test_batch_size_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="Batch size must be >= 1"):
            TranscriptionConfig(batch_size=0, compute_type="float32")

    def test_negative_batch_size_raises(self) -> None:
        with pytest.raises(ValueError, match="Batch size must be >= 1"):
            TranscriptionConfig(batch_size=-5, compute_type="float32")

    def test_diarize_without_token_raises(self) -> None:
        with pytest.raises(ValueError, match="HuggingFace token"):
            TranscriptionConfig(diarize=True, hf_token=None, compute_type="float32")

    def test_diarize_with_token_ok(self) -> None:
        cfg = TranscriptionConfig(
            diarize=True, hf_token="hf_fake", compute_type="float32"
        )
        assert cfg.diarize is True
        assert cfg.hf_token == "hf_fake"

    def test_auto_compute_type_resolved(self) -> None:
        cfg = TranscriptionConfig(device="cpu")
        assert cfg.compute_type == "float32"

    def test_cache_dir_defaults_when_none(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32")
        assert cfg.cache_dir is not None
        assert isinstance(cfg.cache_dir, Path)


# ---------------------------------------------------------------------------
# TranscriptionConfig.with_overrides
# ---------------------------------------------------------------------------


class TestWithOverrides:
    """Frozen config replacement via with_overrides."""

    def test_override_single_field(self) -> None:
        cfg = TranscriptionConfig(compute_type="float32")
        new = cfg.with_overrides(batch_size=8)
        assert new.batch_size == 8
        assert cfg.batch_size == 16  # original unchanged

    def test_override_compute_type(self) -> None:
        cfg = TranscriptionConfig(compute_type="float16")
        new = cfg.with_overrides(compute_type="float32")
        assert new.compute_type == "float32"


# ---------------------------------------------------------------------------
# CacheConfig validators
# ---------------------------------------------------------------------------


class TestCacheConfigValidation:
    """Validation logic specific to CacheConfig."""

    def test_invalid_model_in_csv_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid model sizes"):
            CacheConfig(model="large-v3,bogus")

    def test_valid_csv_models_accepted(self) -> None:
        cfg = CacheConfig(model="tiny,base,small")
        assert cfg.models == ["tiny", "base", "small"]

    def test_invalid_device_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid device"):
            CacheConfig(device="npu")

    def test_languages_empty_returns_empty(self) -> None:
        cfg = CacheConfig(language="")
        assert cfg.languages == []

    def test_languages_csv_parsed(self) -> None:
        cfg = CacheConfig(language="en,de,fr")
        assert cfg.languages == ["en", "de", "fr"]

    def test_cache_dir_defaults_when_none(self) -> None:
        cfg = CacheConfig()
        assert cfg.cache_dir is not None
