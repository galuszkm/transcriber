"""transcriber: Local audio transcription tool using WhisperX.

Import from the submodules you need::

    from transcriber.core import TranscriptionConfig, TranscriptResult
    from transcriber.pipeline import TranscriptionPipeline
    from transcriber.io import OutputFormat, TranscriptWriter
    from transcriber.client import start_recording, stop_recording, transcribe_rest

The heavy ML dependencies are optional.  Install the extras you need::

    pip install transcriber[cli]       # CLI transcription
    pip install transcriber[server]    # HTTP/WebSocket server
    pip install transcriber[client]    # Microphone recording client

Package layout::

    transcriber/
        core/        - Config dataclass, Pydantic models
        io/          - Audio decoding (PyAV), transcript writers
        pipeline/    - Transcription, alignment, diarization
        cli/         - Argument parsing, Rich display, entry point
        server/      - FastAPI HTTP/WebSocket server
        client/      - Microphone recording, REST/WS sender
"""

import logging
from importlib.metadata import version

__version__: str = version("transcriber")

logger = logging.getLogger(__name__)

# Initialise environment (cache dirs, logger suppression, TF32)
# when ML extras are installed.  Silently skipped for client-only installs.
try:
    from . import _env

    _env.init()
except Exception as e:
    logger.warning("Environment initialization failed: %s", e)
    pass
