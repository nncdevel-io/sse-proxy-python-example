import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from sse_proxy_python_example.config import Settings, get_settings
from sse_proxy_python_example.models import ProxyRequest
from sse_proxy_python_example.streaming import (
    proxy_event_stream,
    stream_aiohttp,
    stream_httpx,
    stream_openai_sdk,
)

AppStreamer = Callable[[dict[str, Any]], AsyncIterator[bytes]]
logger = logging.getLogger("sse_proxy_python_example")


def build_access_urls(settings: Settings) -> list[str]:
    base_url = settings.public_base_url.rstrip("/")
    return [
        f"Health check: {base_url}/healthz",
        f"OpenAI Python SDK: {base_url}/openai-python/responses",
        f"httpx: {base_url}/httpx/responses",
        f"aiohttp: {base_url}/aiohttp/responses",
    ]


def _streaming_response(stream: AsyncIterator[bytes]) -> StreamingResponse:
    return StreamingResponse(
        proxy_event_stream(stream),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _bind_streamer(
    settings: Settings,
    stream_func: Callable[[Settings, dict[str, Any]], AsyncIterator[bytes]],
) -> AppStreamer:
    async def streamer(payload: dict[str, Any]) -> AsyncIterator[bytes]:
        async for chunk in stream_func(settings, payload):
            yield chunk

    return streamer


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("SSE proxy access URLs:")
        for line in app.state.access_urls:
            logger.info("  %s", line)
        yield

    app = FastAPI(title="SSE Proxy Python Example", lifespan=lifespan)

    app.state.openai_streamer = _bind_streamer(resolved_settings, stream_openai_sdk)
    app.state.httpx_streamer = _bind_streamer(resolved_settings, stream_httpx)
    app.state.aiohttp_streamer = _bind_streamer(resolved_settings, stream_aiohttp)
    app.state.access_urls = build_access_urls(resolved_settings)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/openai-python/responses")
    async def openai_python_responses(body: ProxyRequest, request: Request) -> StreamingResponse:
        payload = body.to_llm_payload(resolved_settings)
        return _streaming_response(request.app.state.openai_streamer(payload))

    @app.post("/httpx/responses")
    async def httpx_responses(body: ProxyRequest, request: Request) -> StreamingResponse:
        payload = body.to_llm_payload(resolved_settings)
        return _streaming_response(request.app.state.httpx_streamer(payload))

    @app.post("/aiohttp/responses")
    async def aiohttp_responses(body: ProxyRequest, request: Request) -> StreamingResponse:
        payload = body.to_llm_payload(resolved_settings)
        return _streaming_response(request.app.state.aiohttp_streamer(payload))

    return app


app = create_app()
