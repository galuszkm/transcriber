"""Tests for transcriber.cli.cache - config building and cache checking logic."""

import argparse
from pathlib import Path

from transcriber.cli.cache import _build_config, _build_parser, _is_hf_cached

# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildCacheParser:
    """Cache CLI parser construction."""

    def test_defaults(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.models is None
        assert args.languages is None
        assert args.device is None
        assert args.diarize is None
        assert args.cache_dir is None
        assert args.all is False
        assert args.check is False

    def test_all_flag(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--all"])
        assert args.all is True

    def test_check_flag(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--check"])
        assert args.check is True

    def test_models_and_languages(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "--models",
                "tiny",
                "base",
                "--languages",
                "en",
                "de",
                "--device",
                "cpu",
            ]
        )
        assert args.models == ["tiny", "base"]
        assert args.languages == ["en", "de"]
        assert args.device == "cpu"


# ---------------------------------------------------------------------------
# _build_config
# ---------------------------------------------------------------------------


class TestBuildConfig:
    """Config building from CLI args with env defaults."""

    def test_all_flag_overrides_everything(self) -> None:
        args = argparse.Namespace(
            all=True,
            models=None,
            languages=None,
            device=None,
            diarize=None,
            cache_dir=None,
        )
        config = _build_config(args)
        # All model sizes are included
        assert "tiny" in config.models
        assert "large-v3" in config.models
        assert config.diarize is True
        assert config.device == "cpu"

    def test_cli_overrides_applied(self) -> None:
        args = argparse.Namespace(
            all=False,
            models=["tiny", "base"],
            languages=["en"],
            device="cpu",
            diarize=True,
            cache_dir=Path("/tmp/test-cache"),
        )
        config = _build_config(args)
        assert config.models == ["tiny", "base"]
        assert config.languages == ["en"]
        assert config.device == "cpu"
        assert config.diarize is True

    def test_no_overrides_uses_defaults(self) -> None:
        args = argparse.Namespace(
            all=False,
            models=None,
            languages=None,
            device=None,
            diarize=None,
            cache_dir=None,
        )
        config = _build_config(args)
        # Falls back to CacheConfig defaults
        assert "large-v3" in config.models


# ---------------------------------------------------------------------------
# _is_hf_cached
# ---------------------------------------------------------------------------


class TestIsHfCached:
    """HuggingFace model cache detection."""

    def test_not_cached(self, tmp_path: Path) -> None:
        assert _is_hf_cached(tmp_path, "org/model") is False

    def test_cached_with_snapshots(self, tmp_path: Path) -> None:
        snap = tmp_path / "models--org--model" / "snapshots" / "abc123"
        snap.mkdir(parents=True)
        (snap / "model.bin").write_bytes(b"\x00")
        assert _is_hf_cached(tmp_path, "org/model") is True

    def test_empty_snapshots_dir(self, tmp_path: Path) -> None:
        snap = tmp_path / "models--org--model" / "snapshots"
        snap.mkdir(parents=True)
        assert _is_hf_cached(tmp_path, "org/model") is False
