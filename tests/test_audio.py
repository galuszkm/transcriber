"""Tests for transcriber.io.audio - validation and splitting logic."""

from pathlib import Path

import numpy as np
import pytest

from transcriber.io.audio import SAMPLE_RATE, split_audio, validate_audio_file

# ---------------------------------------------------------------------------
# validate_audio_file
# ---------------------------------------------------------------------------


class TestValidateAudioFile:
    """File existence and format validation."""

    def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            validate_audio_file(tmp_path / "nope.wav")

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "file.txt"
        bad.write_text("not audio")
        with pytest.raises(ValueError, match="Unsupported audio format"):
            validate_audio_file(bad)

    def test_valid_wav_passes(self, tmp_path: Path) -> None:
        wav = tmp_path / "test.wav"
        wav.write_bytes(b"\x00")
        result = validate_audio_file(wav)
        assert result.is_absolute()
        assert result.suffix == ".wav"

    def test_valid_mp3_passes(self, tmp_path: Path) -> None:
        mp3 = tmp_path / "test.mp3"
        mp3.write_bytes(b"\x00")
        result = validate_audio_file(mp3)
        assert result.suffix == ".mp3"

    def test_case_insensitive_extension(self, tmp_path: Path) -> None:
        """Extensions are lowered before checking."""
        upper = tmp_path / "test.WAV"
        upper.write_bytes(b"\x00")
        result = validate_audio_file(upper)
        assert result.suffix == ".WAV"


# ---------------------------------------------------------------------------
# split_audio
# ---------------------------------------------------------------------------


class TestSplitAudio:
    """Audio array chunking logic."""

    def test_short_audio_single_chunk(self) -> None:
        audio = np.zeros(SAMPLE_RATE * 5, dtype=np.float32)  # 5 seconds
        chunks = split_audio(audio, chunk_duration_seconds=600)
        assert len(chunks) == 1
        assert len(chunks[0]) == SAMPLE_RATE * 5

    def test_exact_split(self) -> None:
        # 20 seconds split into 10-second chunks
        audio = np.ones(SAMPLE_RATE * 20, dtype=np.float32)
        chunks = split_audio(audio, chunk_duration_seconds=10)
        assert len(chunks) == 2
        assert all(len(c) == SAMPLE_RATE * 10 for c in chunks)

    def test_remainder_chunk(self) -> None:
        # 25 seconds split into 10-second chunks → 3 chunks (10,10,5)
        audio = np.ones(SAMPLE_RATE * 25, dtype=np.float32)
        chunks = split_audio(audio, chunk_duration_seconds=10)
        assert len(chunks) == 3
        assert len(chunks[-1]) == SAMPLE_RATE * 5

    def test_zero_duration_raises(self) -> None:
        audio = np.ones(100, dtype=np.float32)
        with pytest.raises(ValueError, match="must be positive"):
            split_audio(audio, chunk_duration_seconds=0)

    def test_negative_duration_raises(self) -> None:
        audio = np.ones(100, dtype=np.float32)
        with pytest.raises(ValueError, match="must be positive"):
            split_audio(audio, chunk_duration_seconds=-1)

    def test_chunks_are_float32(self) -> None:
        audio = np.ones(SAMPLE_RATE, dtype=np.float64)
        chunks = split_audio(audio, chunk_duration_seconds=1)
        assert all(c.dtype == np.float32 for c in chunks)

    def test_empty_audio_returns_original(self) -> None:
        audio = np.array([], dtype=np.float32)
        chunks = split_audio(audio, chunk_duration_seconds=10)
        # Falls back to [audio] when no chunks produced
        assert len(chunks) == 1
