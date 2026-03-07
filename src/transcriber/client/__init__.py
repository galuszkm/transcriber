"""Transcription client — record audio and send to the service.

Pure-function API for GUI integration::

    from transcriber.client import start_recording, stop_recording, transcribe_sse
"""

from .recorder import (
    RecordingError,
    is_recording,
    list_devices,
    list_input_devices,
    start_recording,
    stop_recording,
)
from .sender import transcribe_rest, transcribe_sse, transcribe_ws

__all__ = [
    "RecordingError",
    "is_recording",
    "list_devices",
    "list_input_devices",
    "start_recording",
    "stop_recording",
    "transcribe_rest",
    "transcribe_sse",
    "transcribe_ws",
]
