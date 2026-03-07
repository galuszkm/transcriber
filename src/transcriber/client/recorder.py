"""Microphone audio recording with start/stop control.

Designed for GUI integration (e.g. PySide6): call :func:`start_recording`
when the user clicks *Record* and :func:`stop_recording` when they click
*Stop*.  A background thread captures audio; the caller never blocks.

Example::

    from transcriber.client import start_recording, stop_recording, list_devices

    start_recording(device=2)
    # ... user clicks stop ...
    wav_bytes = stop_recording()
"""

from __future__ import annotations

import io
import threading
import wave

import numpy as np
import sounddevice as sd

DEFAULT_SAMPLE_RATE: int = 16_000
DEFAULT_CHANNELS: int = 1
DEFAULT_MAX_DURATION: float = 120.0

_lock = threading.Lock()
_state: _RecordingState | None = None


class RecordingError(RuntimeError):
    """Raised on invalid recording operations."""


class _RecordingState:
    """Internal mutable state for an active recording session."""

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        max_duration: float,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_duration = max_duration
        self.chunks: list[np.ndarray] = []
        self.stream: sd.InputStream | None = None
        self.stopped = threading.Event()


def list_devices() -> str:
    """Return a human-readable listing of available audio devices."""
    return str(sd.query_devices())


def list_input_devices() -> list[tuple[int, str]]:
    """Return a list of ``(index, name)`` for available input devices."""
    devices = sd.query_devices()
    return [
        (i, dev["name"])
        for i, dev in enumerate(devices)
        if dev["max_input_channels"] > 0
    ]


def is_recording() -> bool:
    """Return ``True`` if a recording session is currently active."""
    with _lock:
        return _state is not None


def start_recording(
    *,
    device: int | None = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_CHANNELS,
    max_duration: float = DEFAULT_MAX_DURATION,
) -> None:
    """Begin capturing audio from the microphone.

    This returns immediately.  Audio is collected in a background
    thread until :func:`stop_recording` is called or *max_duration*
    seconds have elapsed.

    Args:
        device: Input device index (``None`` = system default).
        sample_rate: Sample rate in Hz (default 16 000).
        channels: Number of audio channels (default 1 / mono).
        max_duration: Safety cap in seconds (default 120).

    Raises:
        RecordingError: If a recording is already in progress.
    """
    global _state

    with _lock:
        if _state is not None:
            raise RecordingError("A recording is already in progress.")

        state = _RecordingState(sample_rate, channels, max_duration)
        max_frames = int(max_duration * sample_rate)

        def _callback(
            indata: np.ndarray,
            frame_count: int,
            time_info: object,
            status: sd.CallbackFlags,
        ) -> None:
            state.chunks.append(indata.copy())
            total = sum(c.shape[0] for c in state.chunks)
            if total >= max_frames:
                state.stopped.set()

        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=device,
            callback=_callback,
        )
        state.stream = stream
        stream.start()
        _state = state


def stop_recording() -> bytes:
    """Stop the current recording and return WAV bytes.

    Returns:
        In-memory WAV file as ``bytes``.

    Raises:
        RecordingError: If no recording is in progress.
    """
    global _state

    with _lock:
        state = _state
        if state is None:
            raise RecordingError("No recording in progress.")
        _state = None

    if state.stream is not None:
        state.stream.stop()
        state.stream.close()

    if not state.chunks:
        frames = np.empty((0, state.channels), dtype="int16")
    else:
        frames = np.concatenate(state.chunks)

    return _frames_to_wav(
        frames, sample_rate=state.sample_rate, channels=state.channels
    )


def _frames_to_wav(
    frames: np.ndarray,
    *,
    sample_rate: int,
    channels: int,
) -> bytes:
    """Encode raw int16 frames as a WAV byte string."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes per sample
        wf.setframerate(sample_rate)
        wf.writeframes(frames.tobytes())
    return buf.getvalue()
