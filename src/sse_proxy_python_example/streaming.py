import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import aiohttp
import httpx
from openai import AsyncOpenAI

from sse_proxy_python_example.config import Settings

Streamer = Callable[[dict[str, Any]], AsyncIterator[bytes]]


class UpstreamError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def error_event(message: str) -> bytes:
    data = json.dumps({"error": message}, ensure_ascii=False)
    return f"event: error\ndata: {data}\n\n".encode()


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, UpstreamError):
        if exc.status_code is None:
            return str(exc)
        return f"Upstream LLM API returned HTTP {exc.status_code}."
    return "LLM stream failed."


async def proxy_event_stream(stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    try:
        async for chunk in stream:
            if chunk:
                yield chunk
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        yield error_event(_safe_error_message(exc))


async def stream_openai_sdk(settings: Settings, payload: dict[str, Any]) -> AsyncIterator[bytes]:
    client = AsyncOpenAI(base_url=str(settings.base_url), api_key=settings.api_key_value)
    try:
        stream = await client.responses.create(**payload)
        async for event in stream:
            event_type = getattr(event, "type", "message")
            event_data = event.model_dump_json()
            yield f"event: {event_type}\ndata: {event_data}\n\n".encode()
    except Exception as exc:
        raise UpstreamError("OpenAI SDK stream failed.") from exc
    finally:
        await client.close()


async def stream_httpx(settings: Settings, payload: dict[str, Any]) -> AsyncIterator[bytes]:
    url = str(settings.base_url).rstrip("/") + "/responses"
    headers = {
        "Authorization": f"Bearer {settings.api_key_value}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(settings.request_timeout, read=None)

    async with (
        httpx.AsyncClient(timeout=timeout) as client,
        client.stream("POST", url, headers=headers, json=payload) as response,
    ):
        if response.status_code < 200 or response.status_code >= 300:
            await response.aread()
            raise UpstreamError("Upstream LLM API failed.", response.status_code)
        async for chunk in response.aiter_bytes():
            yield chunk


async def stream_aiohttp(settings: Settings, payload: dict[str, Any]) -> AsyncIterator[bytes]:
    url = str(settings.base_url).rstrip("/") + "/responses"
    headers = {
        "Authorization": f"Bearer {settings.api_key_value}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=settings.request_timeout, sock_read=None)

    async with (
        aiohttp.ClientSession(timeout=timeout) as session,
        session.post(url, headers=headers, json=payload) as response,
    ):
        if response.status < 200 or response.status >= 300:
            await response.read()
            raise UpstreamError("Upstream LLM API failed.", response.status)
        async for chunk in response.content.iter_any():
            yield chunk
