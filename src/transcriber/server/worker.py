"""Background inference worker using asyncio.Queue + to_thread.

Manages a single :class:`TranscriptionPipeline` instance behind an
async job queue.  The model is loaded eagerly at startup.  Inference
runs in a thread via ``asyncio.to_thread`` so the event loop stays
responsive (PyTorch releases the GIL during CUDA/C++ operations).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..core.config import TranscriptionConfig
from ..core.models import TranscriptResult
from ..pipeline.transcriber import TranscriptionPipeline
from .schemas import (
    SSECompleteEvent,
    SSEErrorEvent,
    SSEEventType,
    SSEProgressEvent,
    format_sse,
)

logger = logging.getLogger(__name__)


@dataclass
class _InferenceJob:
    """A unit of work for the inference queue."""

    audio: np.ndarray
    diarize: bool
    source_label: str
    future: asyncio.Future[TranscriptResult]
    progress_queue: asyncio.Queue[str | None] | None = field(default=None)


class InferenceWorker:
    """Wraps :class:`TranscriptionPipeline` behind an async job queue.

    Only one inference runs at a time, which is correct for a single
    GPU.  Multiple HTTP/WebSocket handlers can ``submit`` concurrently;
    jobs are processed in FIFO order.
    """

    def __init__(self, config: TranscriptionConfig) -> None:
        """Initialise the worker with pipeline configuration."""
        self._config = config
        self._pipeline: TranscriptionPipeline | None = None
        self._queue: asyncio.Queue[_InferenceJob] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_ready(self) -> bool:
        """Return ``True`` when the model is loaded and the worker is running."""
        return self._pipeline is not None

    @property
    def queue_size(self) -> int:
        """Return the number of pending jobs."""
        return self._queue.qsize()

    async def start(self) -> None:
        """Load the model (in a thread) and start the consumer loop."""
        logger.info(
            "Loading transcription model (%s on %s)...",
            self._config.model,
            self._config.device,
        )
        self._pipeline = await asyncio.to_thread(self._create_pipeline)
        logger.info("Model loaded. Starting inference worker loop.")
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Cancel the consumer loop and wait for it to finish."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def submit(
        self,
        audio: np.ndarray,
        *,
        diarize: bool = False,
        source_label: str = "<api>",
    ) -> TranscriptResult:
        """Submit an inference job and await the result.

        Args:
            audio: 16 kHz mono float32 audio array.
            diarize: Whether to run speaker diarization.
            source_label: Label for the audio source.

        Returns:
            Transcription result.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[TranscriptResult] = loop.create_future()
        job = _InferenceJob(
            audio=audio,
            diarize=diarize,
            source_label=source_label,
            future=future,
        )
        await self._queue.put(job)
        return await future

    async def submit_sse(
        self,
        audio: np.ndarray,
        *,
        diarize: bool = False,
        source_label: str = "<sse>",
    ) -> asyncio.Queue[str | None]:
        """Submit an inference job and return a queue of SSE-formatted events.

        The caller reads formatted SSE strings from the returned queue
        until it receives a sentinel ``None``.

        Args:
            audio: 16 kHz mono float32 audio array.
            diarize: Whether to run speaker diarization.
            source_label: Label for the audio source.

        Returns:
            An :class:`asyncio.Queue` yielding SSE text frames.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[TranscriptResult] = loop.create_future()
        progress_queue: asyncio.Queue[str | None] = asyncio.Queue()
        job = _InferenceJob(
            audio=audio,
            diarize=diarize,
            source_label=source_label,
            future=future,
            progress_queue=progress_queue,
        )
        await self._queue.put(job)
        return progress_queue

    def _create_pipeline(self) -> TranscriptionPipeline:
        """Create the pipeline and eagerly load the model."""
        pipeline = TranscriptionPipeline(self._config)
        pipeline.ensure_ready()
        return pipeline

    async def _consume_loop(self) -> None:
        """Process jobs from the queue sequentially, one at a time."""
        while True:
            job = await self._queue.get()
            try:
                await self._run_job(job)
            finally:
                self._queue.task_done()

    async def _run_job(self, job: _InferenceJob) -> None:
        """Execute a single inference job."""
        loop = asyncio.get_running_loop()
        progress_fn = self._make_progress_fn(loop, job.progress_queue)

        try:
            result = await asyncio.to_thread(
                self._pipeline.run_from_audio,  # type: ignore[union-attr]
                job.audio,
                source_label=job.source_label,
                diarize=job.diarize,
                progress_fn=progress_fn,
            )
            job.future.set_result(result)
            self._send_sse(
                job.progress_queue, "complete", SSECompleteEvent.from_result(result)
            )
        except Exception as exc:
            job.future.set_exception(exc)
            self._send_sse(job.progress_queue, "error", SSEErrorEvent(detail=str(exc)))

    @staticmethod
    def _make_progress_fn(
        loop: asyncio.AbstractEventLoop,
        queue: asyncio.Queue[str | None] | None,
    ) -> Callable[[str, str], None] | None:
        """Build a thread-safe progress callback for SSE streaming."""
        if queue is None:
            return None

        def _on_progress(stage: str, message: str) -> None:
            text = format_sse(
                "progress", SSEProgressEvent(stage=stage, message=message)
            )
            loop.call_soon_threadsafe(queue.put_nowait, text)

        return _on_progress

    @staticmethod
    def _send_sse(
        queue: asyncio.Queue[str | None] | None,
        event: SSEEventType,
        data: SSECompleteEvent | SSEErrorEvent,
    ) -> None:
        """Push a final SSE event plus the ``None`` sentinel to the queue."""
        if queue is None:
            return
        queue.put_nowait(format_sse(event, data))
        queue.put_nowait(None)
