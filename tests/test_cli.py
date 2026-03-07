"""Tests for transcriber.cli - parser, display, and app helpers."""

import argparse
from pathlib import Path
from types import SimpleNamespace

from transcriber.cli.display import _format_timings
from transcriber.cli.parser import add_pipeline_args, build_parser
from transcriber.core.config import TranscriptionConfig

# ---------------------------------------------------------------------------
# build_parser / add_pipeline_args
# ---------------------------------------------------------------------------


class TestBuildParser:
    """CLI argument parser construction and defaults."""

    def test_parser_returns_namespace(self) -> None:
        parser = build_parser("0.1.0")
        args = parser.parse_args(["test.wav"])
        assert args.audio_file == Path("test.wav")

    def test_default_values(self) -> None:
        parser = build_parser("0.1.0")
        args = parser.parse_args(["audio.mp3"])
        assert args.model == "large-v3"
        assert args.device == "cuda"
        assert args.compute_type == "auto"
        assert args.batch_size == 16
        assert args.diarize is False
        assert args.format == "md"
        assert args.output is None

    def test_all_flags(self) -> None:
        parser = build_parser("0.1.0")
        args = parser.parse_args(
            [
                "test.wav",
                "-m",
                "tiny",
                "-d",
                "cpu",
                "-c",
                "float32",
                "-b",
                "4",
                "--diarize",
                "-f",
                "json",
                "-o",
                "out/result",
                "--hf-token",
                "hf_abc",
                "--cache-dir",
                "/tmp/cache",
            ]
        )
        assert args.model == "tiny"
        assert args.device == "cpu"
        assert args.compute_type == "float32"
        assert args.batch_size == 4
        assert args.diarize is True
        assert args.format == "json"
        assert args.output == Path("out/result")
        assert args.hf_token == "hf_abc"
        assert args.cache_dir == Path("/tmp/cache")


class TestAddPipelineArgs:
    """Shared pipeline args used by both CLI and server."""

    def test_default_device_override(self) -> None:
        parser = argparse.ArgumentParser()
        add_pipeline_args(parser, default_device="cpu")
        args = parser.parse_args([])
        assert args.device == "cpu"


# ---------------------------------------------------------------------------
# _format_timings
# ---------------------------------------------------------------------------


class TestFormatTimings:
    """Timing breakdown string builder."""

    def test_without_diarize(self) -> None:
        timings = {"model_load": 2.5, "transcribe": 10.0, "align": 1.0}
        cfg = TranscriptionConfig(compute_type="float32", diarize=False)
        result = _format_timings(timings, cfg)
        assert "Load 2.5s" in result
        assert "Transcribe 10.0s" in result
        assert "Align 1.0s" in result
        assert "Diarize" not in result

    def test_with_diarize(self) -> None:
        timings = {"model_load": 1, "transcribe": 5, "align": 0.5, "diarize": 3}
        cfg = TranscriptionConfig(compute_type="float32", diarize=True, hf_token="hf_x")
        result = _format_timings(timings, cfg)
        assert "Diarize 3.0s" in result

    def test_missing_keys_default_zero(self) -> None:
        result = _format_timings({}, TranscriptionConfig(compute_type="float32"))
        assert "Load 0.0s" in result
        assert "Transcribe 0.0s" in result


# ---------------------------------------------------------------------------
# _config_from_args
# ---------------------------------------------------------------------------


class TestConfigFromArgs:
    """Build TranscriptionConfig from CLI namespace."""

    def test_basic_conversion(self) -> None:
        from transcriber.cli.app import _config_from_args

        args = SimpleNamespace(
            model="tiny",
            device="cpu",
            compute_type="float32",
            batch_size=8,
            diarize=False,
            hf_token=None,
            cache_dir=None,
        )
        cfg = _config_from_args(args)
        assert cfg.model == "tiny"
        assert cfg.device == "cpu"
        assert cfg.batch_size == 8

    def test_with_hf_token_and_cache_dir(self) -> None:
        from transcriber.cli.app import _config_from_args

        args = SimpleNamespace(
            model="base",
            device="cpu",
            compute_type="float32",
            batch_size=16,
            diarize=True,
            hf_token="hf_test",
            cache_dir=Path("/tmp/cache"),
        )
        cfg = _config_from_args(args)
        assert cfg.hf_token == "hf_test"
        assert cfg.cache_dir == Path("/tmp/cache")
        assert cfg.diarize is True
