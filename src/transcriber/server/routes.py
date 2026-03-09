"""HTTP and WebSocket route handlers for the transcription service."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, StreamingResponse

from .audio_decode import decode_audio_bytes, decode_base64_audio
from .schemas import (
    HealthResponse,
    SSEProgressEvent,
    TranscribeRequest,
    TranscribeResponse,
    UTF8JSONResponse,
    format_sse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _health_response(request: Request) -> UTF8JSONResponse:
    """Build a health response with appropriate HTTP status code.

    Returns HTTP 200 when the model is loaded and ready, or HTTP 503
    while still loading.  Used by both ``/health`` and ``/ping``.
    """
    worker = request.app.state.worker
    config = request.app.state.config
    body = HealthResponse(
        status="ready" if worker.is_ready else "loading",
        model_loaded=worker.is_ready,
        model_size=config.model,
        device=config.device,
        queue_size=worker.queue_size,
    )
    status_code = 200 if worker.is_ready else 503
    return UTF8JSONResponse(content=body.model_dump(), status_code=status_code)


async def _submit_transcription(
    request: Request,
    audio: Any,
    *,
    diarize: bool = False,
    source_label: str = "<api>",
) -> UTF8JSONResponse:
    """Submit audio to the inference worker and return the result.

    Shared by all transcription endpoints (``/invocations``,
    ``/transcribe``, ``/transcribe/json``, ``/transcribe/raw``).
    """
    worker = request.app.state.worker
    result = await worker.submit(audio, diarize=diarize, source_label=source_label)
    return UTF8JSONResponse(content=TranscribeResponse.from_result(result).model_dump())


# ---------------------------------------------------------------------------
# Health — shared by /health and /ping
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> UTF8JSONResponse:
    """Return service readiness status with model and queue details."""
    return await _health_response(request)


@router.get("/ping", response_model=HealthResponse)
async def ping(request: Request) -> UTF8JSONResponse:
    """SageMaker health-check endpoint (also usable outside SageMaker).

    Returns HTTP 200 when the model is loaded, or HTTP 503 while still
    loading.  SageMaker calls this endpoint periodically and expects a
    response within 2 seconds.

    See: https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html
    """
    return await _health_response(request)


# ---------------------------------------------------------------------------
# /invocations — SageMaker inference (content-type auto-detection)
# ---------------------------------------------------------------------------


@router.post("/invocations", response_model=TranscribeResponse)
async def invocations(request: Request) -> UTF8JSONResponse | JSONResponse:
    """SageMaker inference endpoint.

    Accepts audio via ``application/octet-stream`` (raw bytes),
    ``application/json`` (JSON body with ``audio_base64``), or
    ``multipart/form-data`` (file upload).

    An optional ``diarize`` query parameter enables speaker diarization.

    See: https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html
    """
    content_type = (request.headers.get("content-type") or "").lower()

    # Determine diarize flag from query parameter.
    diarize = request.query_params.get("diarize", "false").lower() in {
        "true",
        "1",
        "yes",
    }

    if "application/json" in content_type:
        body = await request.json()
        audio_b64 = body.get("audio_base64")
        if not audio_b64:
            return JSONResponse(
                status_code=400,
                content={"detail": "JSON body must include 'audio_base64' field."},
            )
        diarize = diarize or body.get("diarize", False)
        audio = decode_base64_audio(audio_b64)
        label = "<invocations-json>"
    elif "application/octet-stream" in content_type:
        raw_bytes = await request.body()
        if not raw_bytes:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": (
                        "Empty request body. Send audio as raw bytes "
                        "(application/octet-stream), JSON with 'audio_base64', "
                        "or multipart form with 'file' field."
                    )
                },
            )
        audio = decode_audio_bytes(raw_bytes)
        label = "<invocations-raw>"
    elif "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            return JSONResponse(
                status_code=400,
                content={"detail": "Multipart form must include 'file' field."},
            )
        raw_bytes = await upload.read()  # type: ignore[union-attr]
        audio = decode_audio_bytes(raw_bytes)
        label = (
            getattr(upload, "filename", "<invocations-upload>")
            or "<invocations-upload>"
        )
    else:
        # Default: treat as raw bytes for maximum compatibility.
        raw_bytes = await request.body()
        if not raw_bytes:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": (
                        "Empty request body. Send audio as raw bytes "
                        "(application/octet-stream), JSON with 'audio_base64', "
                        "or multipart form with 'file' field."
                    )
                },
            )
        audio = decode_audio_bytes(raw_bytes)
        label = "<invocations>"

    return await _submit_transcription(
        request, audio, diarize=diarize, source_label=label
    )


# ---------------------------------------------------------------------------
# REST — multipart file upload or base64 form field
# ---------------------------------------------------------------------------


_FILE_NONE = File(None)
_FORM_NONE = Form(None)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    request: Request,
    file: UploadFile | None = _FILE_NONE,
    audio_base64: str | None = _FORM_NONE,
    diarize: bool = Query(default=False),
) -> UTF8JSONResponse | JSONResponse:
    """Transcribe audio from a file upload or base64 form field."""
    if file is not None:
        raw_bytes = await file.read()
        audio = decode_audio_bytes(raw_bytes)
        label = file.filename or "<upload>"
    elif audio_base64 is not None:
        audio = decode_base64_audio(audio_base64)
        label = "<base64>"
    else:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Provide 'file' (multipart) or 'audio_base64' (form field)."
            },
        )

    return await _submit_transcription(
        request, audio, diarize=diarize, source_label=label
    )


# ---------------------------------------------------------------------------
# REST — JSON body with base64 audio
# ---------------------------------------------------------------------------


@router.post("/transcribe/json", response_model=TranscribeResponse)
async def transcribe_json(
    request: Request,
    body: TranscribeRequest,
) -> UTF8JSONResponse:
    """Transcribe audio from a JSON body with base64-encoded data."""
    audio = decode_base64_audio(body.audio_base64)
    return await _submit_transcription(
        request, audio, diarize=body.diarize, source_label="<json>"
    )


# ---------------------------------------------------------------------------
# REST — raw bytes in request body
# ---------------------------------------------------------------------------


@router.post("/transcribe/raw", response_model=TranscribeResponse)
async def transcribe_raw(
    request: Request,
    diarize: bool = Query(default=False),
) -> UTF8JSONResponse:
    """Transcribe audio from raw bytes (Content-Type: application/octet-stream)."""
    raw_bytes = await request.body()
    audio = decode_audio_bytes(raw_bytes)
    return await _submit_transcription(
        request, audio, diarize=diarize, source_label="<raw>"
    )


# ---------------------------------------------------------------------------
# SSE — streaming progress events via Server-Sent Events
# ---------------------------------------------------------------------------


_SSE_KEEPALIVE_INTERVAL: float = 15.0
_SSE_KEEPALIVE_FRAME: str = ": keepalive\n\n"


async def _sse_generator(
    event_queue: asyncio.Queue[str | None],
) -> AsyncGenerator[str, None]:
    """Async generator that drains the event queue for StreamingResponse.

    Emits a comment keep-alive frame every ``_SSE_KEEPALIVE_INTERVAL`` seconds
    while waiting for the next event.  This prevents HTTP proxies and load
    balancers from closing the connection during long inference runs or queue
    wait times.  SSE comment lines are silently ignored by all compliant
    clients (browsers, ``httpx``, ``EventSource``).
    """
    while True:
        try:
            frame = await asyncio.wait_for(
                event_queue.get(), timeout=_SSE_KEEPALIVE_INTERVAL
            )
        except TimeoutError:
            yield _SSE_KEEPALIVE_FRAME
            continue
        if frame is None:
            return
        yield frame


@router.post("/transcribe/stream", response_model=None)
async def transcribe_stream(
    request: Request,
    file: UploadFile | None = _FILE_NONE,
    audio_base64: str | None = _FORM_NONE,
    diarize: bool = Query(default=False),
) -> StreamingResponse | JSONResponse:
    """Transcribe audio with progress via Server-Sent Events.

    Accepts the same inputs as ``/transcribe`` (multipart file or
    base64 form field).  Returns ``text/event-stream`` with:

    - ``event: progress`` — stage updates during pipeline execution.
    - ``event: complete`` — final transcription result.
    - ``event: error`` — if an error occurs.

    Compatible with browser ``EventSource``, ``fetch()``, curl
    (``--no-buffer``), and Python ``httpx.stream()``.
    """
    worker = request.app.state.worker

    if file is not None:
        raw_bytes = await file.read()
        audio = decode_audio_bytes(raw_bytes)
        label = file.filename or "<upload>"
    elif audio_base64 is not None:
        audio = decode_base64_audio(audio_base64)
        label = "<base64>"
    else:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Provide 'file' (multipart) or 'audio_base64' (form field)."
            },
        )

    event_queue = await worker.submit_sse(audio, diarize=diarize, source_label=label)

    # Send an immediate "queued" event so the client knows we accepted it.
    event_queue.put_nowait(
        format_sse("progress", SSEProgressEvent(stage="queued", message="Job accepted"))
    )

    return StreamingResponse(
        _sse_generator(event_queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/transcribe/json/stream", response_model=None)
async def transcribe_json_stream(
    request: Request,
    body: TranscribeRequest,
) -> StreamingResponse:
    """Transcribe base64 JSON audio with progress via Server-Sent Events."""
    worker = request.app.state.worker
    audio = decode_base64_audio(body.audio_base64)

    event_queue = await worker.submit_sse(
        audio, diarize=body.diarize, source_label="<json>"
    )
    event_queue.put_nowait(
        format_sse("progress", SSEProgressEvent(stage="queued", message="Job accepted"))
    )

    return StreamingResponse(
        _sse_generator(event_queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/transcribe/raw/stream", response_model=None)
async def transcribe_raw_stream(
    request: Request,
    diarize: bool = Query(default=False),
) -> StreamingResponse:
    """Transcribe raw audio bytes with progress via Server-Sent Events."""
    worker = request.app.state.worker
    raw_bytes = await request.body()
    audio = decode_audio_bytes(raw_bytes)

    event_queue = await worker.submit_sse(audio, diarize=diarize, source_label="<raw>")
    event_queue.put_nowait(
        format_sse("progress", SSEProgressEvent(stage="queued", message="Job accepted"))
    )

    return StreamingResponse(
        _sse_generator(event_queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# WebSocket — send binary audio, receive JSON transcript
# ---------------------------------------------------------------------------


@router.websocket("/ws/transcribe")
async def ws_transcribe(
    websocket: WebSocket,
    diarize: bool = Query(default=False),
) -> None:
    """WebSocket endpoint for continuous transcription.

    Protocol:
        Client → Server: binary frame with complete audio file bytes.
        Server → Client: JSON text frame with transcription result.

    The ``diarize`` query parameter applies to all messages on the connection.
    """
    await websocket.accept()
    worker = websocket.app.state.worker

    try:
        while True:
            data = await websocket.receive_bytes()

            try:
                audio = decode_audio_bytes(data)
                result = await worker.submit(
                    audio, diarize=diarize, source_label="<ws>"
                )
                resp = TranscribeResponse.from_result(result)
                await websocket.send_json(
                    {
                        "status": "ok",
                        **resp.model_dump(),
                    }
                )
            except Exception as exc:
                logger.exception("WebSocket transcription error")
                await websocket.send_json(
                    {
                        "status": "error",
                        "detail": str(exc),
                    }
                )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
