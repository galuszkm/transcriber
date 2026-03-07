"""Tests for transcriber.cli.cache - cache check and download logic."""

from pathlib import Path
from unittest.mock import patch

import transcriber._env as env_mod
from transcriber.cli.cache import _check_cache, _download_diarization, _download_nltk
from transcriber.core.config import CacheConfig


class TestCheckCache:
    """_check_cache filesystem inspection."""

    def test_empty_cache_reports_failure(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)

        config = CacheConfig(model="tiny", device="cpu")
        result = _check_cache(config, ["en"])
        assert result == 1  # not all present

    def test_all_cached_reports_success(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)

        # Create punkt_tab
        punkt = tmp_path / "nltk" / "tokenizers" / "punkt_tab"
        punkt.mkdir(parents=True)

        # Create whisper model snapshot
        snap = (
            tmp_path
            / "huggingface"
            / "hub"
            / "models--Systran--faster-whisper-tiny"
            / "snapshots"
            / "abc"
        )
        snap.mkdir(parents=True)
        (snap / "model.bin").write_bytes(b"\x00")

        # No languages to check
        config = CacheConfig(model="tiny", device="cpu")
        result = _check_cache(config, [])
        assert result == 0

    def test_diarize_check_no_models(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)

        # Create punkt_tab and whisper model so only diarize fails
        punkt = tmp_path / "nltk" / "tokenizers" / "punkt_tab"
        punkt.mkdir(parents=True)
        snap = (
            tmp_path
            / "huggingface"
            / "hub"
            / "models--Systran--faster-whisper-tiny"
            / "snapshots"
            / "abc"
        )
        snap.mkdir(parents=True)
        (snap / "model.bin").write_bytes(b"\x00")

        config = CacheConfig(model="tiny", device="cpu", diarize=True)
        result = _check_cache(config, [])
        # diarize models not found → failure
        assert result == 1

    def test_diarize_check_with_models(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)

        # Set up all prerequisites
        punkt = tmp_path / "nltk" / "tokenizers" / "punkt_tab"
        punkt.mkdir(parents=True)
        snap = (
            tmp_path
            / "huggingface"
            / "hub"
            / "models--Systran--faster-whisper-tiny"
            / "snapshots"
            / "abc"
        )
        snap.mkdir(parents=True)
        (snap / "model.bin").write_bytes(b"\x00")

        # Create pyannote models
        pyannote = (
            tmp_path
            / "huggingface"
            / "hub"
            / "models--pyannote--segmentation"
            / "snapshots"
            / "def"
        )
        pyannote.mkdir(parents=True)
        (pyannote / "model.pt").write_bytes(b"\x00")

        config = CacheConfig(model="tiny", device="cpu", diarize=True)
        result = _check_cache(config, [])
        assert result == 0


class TestDownloadNltk:
    """NLTK download wrapper."""

    def test_success(self, tmp_path: Path) -> None:
        with patch("transcriber.cli.cache.nltk") as mock_nltk:
            mock_nltk.download.return_value = True
            assert _download_nltk(tmp_path) is True
            mock_nltk.download.assert_called_once()

    def test_failure_returns_false(self, tmp_path: Path) -> None:
        with patch("transcriber.cli.cache.nltk") as mock_nltk:
            mock_nltk.download.side_effect = RuntimeError("fail")
            assert _download_nltk(tmp_path) is False


class TestDownloadDiarization:
    """Diarization download wrapper."""

    def test_no_token_returns_false(self) -> None:
        config = CacheConfig(diarize=True, hf_token=None)
        assert _download_diarization(config) is False

    def test_with_token_success(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)

        config = CacheConfig(
            diarize=True, hf_token="hf_test", device="cpu"
        )
        with patch("transcriber.cli.cache.DiarizationPipeline"):
            assert _download_diarization(config) is True

    def test_with_token_failure(self, tmp_path: Path) -> None:
        env_mod._initialized = False
        env_mod.init(cache_path=tmp_path)

        config = CacheConfig(
            diarize=True, hf_token="hf_test", device="cpu"
        )
        with patch(
            "transcriber.cli.cache.DiarizationPipeline",
            side_effect=RuntimeError("fail"),
        ):
            assert _download_diarization(config) is False
