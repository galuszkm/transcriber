"""Tests for transcriber.server.routes - SSE generator and route helpers."""

import asyncio

import pytest

from transcriber.server.routes import _sse_generator


@pytest.mark.asyncio
async def test_sse_generator_yields_frames() -> None:
    """Generator yields frames and stops at None sentinel."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    queue.put_nowait("event: progress\ndata: {}\n\n")
    queue.put_nowait("event: complete\ndata: {}\n\n")
    queue.put_nowait(None)

    frames = []
    async for frame in _sse_generator(queue):
        frames.append(frame)

    assert len(frames) == 2
    assert "progress" in frames[0]
    assert "complete" in frames[1]


@pytest.mark.asyncio
async def test_sse_generator_stops_on_none() -> None:
    """Generator terminates when it receives None."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    queue.put_nowait(None)

    frames = []
    async for frame in _sse_generator(queue):
        frames.append(frame)

    assert frames == []
