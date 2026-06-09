from collections.abc import AsyncIterator

import pytest

from sse_proxy_python_example.streaming import UpstreamError, proxy_event_stream


async def failing_stream() -> AsyncIterator[bytes]:
    yield b"event: response.created\n\n"
    raise UpstreamError("secret upstream body", status_code=502)


@pytest.mark.asyncio
async def test_proxy_event_stream_emits_sanitized_error_event() -> None:
    chunks = [chunk async for chunk in proxy_event_stream(failing_stream())]

    assert chunks == [
        b"event: response.created\n\n",
        b'event: error\ndata: {"error": "Upstream LLM API returned HTTP 502."}\n\n',
    ]
    assert b"secret upstream body" not in b"".join(chunks)

