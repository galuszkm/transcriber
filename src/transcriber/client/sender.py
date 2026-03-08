"""Send audio to the transcription service.

Provides :func:`transcribe_rest` and :func:`transcribe_ws` for
submitting WAV bytes and receiving the parsed result dict.

Example::

    from transcriber.client import transcribe_rest, transcribe_ws

    result = transcribe_rest(wav_bytes)
    result = transcribe_ws(wav_bytes, url="ws://localhost:9876")
"""

from __future__ import annotations

import asyncio
import json
import ssl
from collections.abc import Callable, Iterator

import httpx
import websockets

DEFAULT_URL: str = "http://localhost:8000"
_TIMEOUT: float = 300.0


def transcribe_rest(
    wav_bytes: bytes,
    *,
    url: str = DEFAULT_URL,
    diarize: bool = False,
    timeout: float = _TIMEOUT,
    verify_ssl: bool = True,
) -> dict:
    """Send audio via REST and return the transcription result.

    Args:
        wav_bytes: WAV file bytes.
        url: Base URL of the transcription service.
        diarize: Whether to enable speaker diarization.
        timeout: Request timeout in seconds.
        verify_ssl: Verify the server's TLS certificate. Set to ``False``
            to skip validation (e.g. self-signed certs).

    Returns:
        Parsed JSON response dict.
    """
    endpoint = f"{url}/transcribe"
    files = {"file": ("recording.wav", wav_bytes, "audio/wav")}
    params = {"diarize": str(diarize).lower()}

    resp = httpx.post(
        endpoint, files=files, params=params, timeout=timeout, verify=verify_ssl
    )
    resp.raise_for_status()
    return resp.json()


def transcribe_sse(
    wav_bytes: bytes,
    *,
    url: str = DEFAULT_URL,
    diarize: bool = False,
    timeout: float = _TIMEOUT,
    on_progress: Callable[[str, str], None] | None = None,
    verify_ssl: bool = True,
) -> dict:
    """Send audio via SSE streaming and return the transcription result.

    Uses ``/transcribe/raw/stream``.  Progress events are delivered to
    *on_progress* as they arrive; the function blocks until the server
    sends the ``complete`` event.  Prefer this over :func:`transcribe_rest`
    for large files to avoid HTTP timeouts.

    Args:
        wav_bytes: WAV file bytes.
        url: Base URL of the transcription service.
        diarize: Whether to enable speaker diarization.
        timeout: Connection + read timeout in seconds.
        on_progress: Optional callback invoked for each ``progress`` event
            with ``(stage, message)`` arguments.
        verify_ssl: Verify the server's TLS certificate. Set to ``False``
            to skip validation (e.g. self-signed certs).

    Returns:
        Parsed JSON result dict (same shape as :func:`transcribe_rest`).

    Raises:
        RuntimeError: If the server sends an ``error`` event.
    """
    endpoint = f"{url}/transcribe/raw/stream"
    params = {"diarize": str(diarize).lower()}

    with httpx.stream(
        "POST",
        endpoint,
        content=wav_bytes,
        headers={"Content-Type": "application/octet-stream"},
        params=params,
        timeout=timeout,
        verify=verify_ssl,
    ) as resp:
        resp.raise_for_status()
        return _parse_sse(resp.iter_lines(), on_progress=on_progress)


def _parse_sse(
    lines: Iterator[str],
    *,
    on_progress: Callable[[str, str], None] | None,
) -> dict:
    """Parse SSE ``event:/data:`` line pairs and return the complete payload."""
    event_type = ""
    data_buf = ""

    for line in lines:
        if line.startswith("event:"):
            event_type = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_buf = line[len("data:") :].strip()
        elif line == "":
            if event_type and data_buf:
                data = json.loads(data_buf)
                if event_type == "complete":
                    return data
                if event_type == "error":
                    detail = data.get("detail", "unknown error")
                    raise RuntimeError(f"Transcription failed: {detail}")
                if event_type == "progress" and on_progress is not None:
                    on_progress(data.get("stage", ""), data.get("message", ""))
            event_type = ""
            data_buf = ""

    msg = "SSE stream ended without a 'complete' event"
    raise RuntimeError(msg)


def transcribe_ws(
    wav_bytes: bytes,
    *,
    url: str = DEFAULT_URL,
    diarize: bool = False,
    verify_ssl: bool = True,
) -> dict:
    """Send audio via WebSocket and return the transcription result.

    Args:
        wav_bytes: WAV file bytes.
        url: Base URL (``http://`` or ``https://``).
        diarize: Whether to enable speaker diarization.
        verify_ssl: Verify the server's TLS certificate. Set to ``False``
            to skip validation (e.g. self-signed certs).

    Returns:
        Parsed JSON response dict.

    Raises:
        RuntimeError: If the server returns an error status.
    """
    return asyncio.run(
        _ws_send(wav_bytes, url=url, diarize=diarize, verify_ssl=verify_ssl)
    )


async def _ws_send(
    wav_bytes: bytes,
    *,
    url: str,
    diarize: bool,
    verify_ssl: bool,
) -> dict:
    """Async WebSocket implementation."""
    ssl_ctx: ssl.SSLContext | bool = bool(verify_ssl)
    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/ws/transcribe?diarize={'true' if diarize else 'false'}"

    async with websockets.connect(
        ws_url, ssl=ssl_ctx if ws_url.startswith("wss://") else None
    ) as ws:
        await ws.send(wav_bytes)
        raw = await ws.recv()
        data = json.loads(raw)

    if data.get("status") != "ok":
        detail = data.get("detail", "unknown error")
        msg = f"Transcription failed: {detail}"
        raise RuntimeError(msg)

    return data
