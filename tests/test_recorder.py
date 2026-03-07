"""Tests for transcriber.client.recorder - WAV encoding and state helpers."""

import wave

import numpy as np

from transcriber.client.recorder import RecordingError, _frames_to_wav, is_recording


class TestFramesToWav:
    """int16 frame data → WAV byte encoding."""

    def test_produces_valid_wav(self) -> None:
        frames = np.array([0, 100, -100, 32767, -32768], dtype="int16")
        wav_bytes = _frames_to_wav(frames, sample_rate=16000, channels=1)
        assert wav_bytes[:4] == b"RIFF"

    def test_wav_parameters(self) -> None:
        frames = np.zeros((160, 1), dtype="int16")
        wav_bytes = _frames_to_wav(frames, sample_rate=16000, channels=1)
        import io

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 16000
            assert wf.getsampwidth() == 2
            assert wf.getnframes() == 160

    def test_stereo_encoding(self) -> None:
        frames = np.zeros((80, 2), dtype="int16")
        wav_bytes = _frames_to_wav(frames, sample_rate=44100, channels=2)
        import io

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            assert wf.getnchannels() == 2
            assert wf.getframerate() == 44100

    def test_empty_frames(self) -> None:
        frames = np.empty((0, 1), dtype="int16")
        wav_bytes = _frames_to_wav(frames, sample_rate=16000, channels=1)
        import io

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            assert wf.getnframes() == 0


class TestRecordingState:
    """Recording state management."""

    def test_is_recording_false_initially(self) -> None:
        assert is_recording() is False

    def test_recording_error_is_runtime_error(self) -> None:
        err = RecordingError("test")
        assert isinstance(err, RuntimeError)
        assert str(err) == "test"
