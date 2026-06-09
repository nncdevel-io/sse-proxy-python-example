from collections.abc import AsyncIterator

import httpx
import pytest

from sse_proxy_python_example.app import build_startup_log_lines, create_app
from sse_proxy_python_example.config import Settings


def test_access_urls_include_health_and_proxy_endpoints() -> None:
    settings = Settings(public_base_url="http://localhost:18000")
    app = create_app(settings)

    assert app.state.access_urls == [
        "Health check: http://localhost:18000/healthz",
        "OpenAI Python SDK: http://localhost:18000/openai-python/responses",
        "httpx: http://localhost:18000/httpx/responses",
        "aiohttp: http://localhost:18000/aiohttp/responses",
    ]


def test_startup_log_lines_report_ssl_cert_file_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", "/path/to/corporate-ca.pem")

    assert "SSL_CERT_FILE: /path/to/corporate-ca.pem" in build_startup_log_lines(
        ["Health check: http://localhost:18000/healthz"]
    )


def test_startup_log_lines_report_ssl_cert_file_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    assert "SSL_CERT_FILE: unset" in build_startup_log_lines(
        ["Health check: http://localhost:18000/healthz"]
    )


async def fake_stream(payload: dict[str, object]) -> AsyncIterator[bytes]:
    assert payload["stream"] is True
    yield b"event: response.output_text.delta\n"
    yield b'data: {"delta":"hi"}\n\n'


@pytest.mark.asyncio
async def test_httpx_endpoint_returns_event_stream() -> None:
    app = create_app()
    app.dependency_overrides.clear()
    app.state.httpx_streamer = fake_stream

    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
        client.stream("POST", "/httpx/responses", json={"input": "hello"}) as response,
    ):
        body = b"".join([chunk async for chunk in response.aiter_bytes()])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body == b'event: response.output_text.delta\ndata: {"delta":"hi"}\n\n'


@pytest.mark.asyncio
async def test_openai_python_endpoint_returns_event_stream() -> None:
    app = create_app()
    app.state.openai_streamer = fake_stream

    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
        client.stream(
            "POST", "/openai-python/responses", json={"input": "hello"}
        ) as response,
    ):
        body = b"".join([chunk async for chunk in response.aiter_bytes()])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body == b'event: response.output_text.delta\ndata: {"delta":"hi"}\n\n'


@pytest.mark.asyncio
async def test_aiohttp_endpoint_returns_event_stream() -> None:
    app = create_app()
    app.state.aiohttp_streamer = fake_stream

    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
        client.stream("POST", "/aiohttp/responses", json={"input": "hello"}) as response,
    ):
        body = b"".join([chunk async for chunk in response.aiter_bytes()])

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert body == b'event: response.output_text.delta\ndata: {"delta":"hi"}\n\n'
