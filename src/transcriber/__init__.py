"""Meeting-Noter: Local audio transcription tool using WhisperX.

Public API re-exports for convenient programmatic usage::

    from transcriber import TranscriptionPipeline, TranscriptionConfig

    pipeline = TranscriptionPipeline(TranscriptionConfig(device="cuda"))
    result = pipeline.run(Path("meeting.wav"))

Package layout::

    transcriber/
        core/        - Config dataclass, Pydantic models
        io/          - Audio decoding (PyAV), transcript writers
        pipeline/    - Transcription, alignment, diarization
        cli/         - Argument parsing, Rich display, entry point
"""

# Initialize environment FIRST, before any other imports that might use NLTK
from importlib.metadata import version

from . import _env

_env.init()

__version__: str = version("transcriber")

from .core.config import TranscriptionConfig  # noqa: E402
from .core.models import TranscriptResult, TranscriptSegment  # noqa: E402
from .io.writer import OutputFormat, TranscriptWriter  # noqa: E402
from .pipeline.transcriber import TranscriptionPipeline  # noqa: E402

__all__ = [
    "OutputFormat",
    "TranscriptResult",
    "TranscriptSegment",
    "TranscriptWriter",
    "TranscriptionConfig",
    "TranscriptionPipeline",
]
