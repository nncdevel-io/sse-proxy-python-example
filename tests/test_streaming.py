from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import APIError
from pydantic import SecretStr

from sse_proxy_python_example.config import Settings
from sse_proxy_python_example.streaming import (
    UpstreamError,
    create_ssl_context,
    get_httpx_verify,
    proxy_event_stream,
    stream_aiohttp,
    stream_openai_sdk,
)


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


async def unexpected_failing_stream() -> AsyncIterator[bytes]:
    raise RuntimeError("proxy password leaked")
    yield b"unreachable"


@pytest.mark.asyncio
async def test_proxy_event_stream_logs_unexpected_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    chunks = [chunk async for chunk in proxy_event_stream(unexpected_failing_stream())]

    assert chunks == [b'event: error\ndata: {"error": "LLM stream failed."}\n\n']
    assert "proxy password leaked" in caplog.text


@pytest.mark.asyncio
async def test_aiohttp_stream_uses_proxy_environment() -> None:
    settings = Settings(api_key=SecretStr("secret"), model="test-model")
    session = MagicMock()
    response = MagicMock()
    response.status = 200
    response.content.iter_any.return_value = empty_async_iterator()
    session.post.return_value.__aenter__.return_value = response

    with (
        patch("sse_proxy_python_example.streaming.aiohttp.ClientSession") as client_session,
        patch("sse_proxy_python_example.streaming.aiohttp.TCPConnector") as connector_factory,
        patch("sse_proxy_python_example.streaming.create_ssl_context") as context_factory,
    ):
        client_session.return_value.__aenter__.return_value = session
        chunks = [chunk async for chunk in stream_aiohttp(settings, {"stream": True})]

    assert chunks == []
    assert client_session.call_args.kwargs["trust_env"] is True
    connector_factory.assert_called_once_with(ssl=context_factory.return_value)
    assert client_session.call_args.kwargs["connector"] is connector_factory.return_value


def test_ssl_context_removes_x509_strict_flag_without_disabling_verification() -> None:
    with patch("sse_proxy_python_example.streaming.ssl.create_default_context") as context_factory:
        context = context_factory.return_value
        context.verify_flags = 0xFFFF
        context.check_hostname = True
        context.verify_mode = 2
        create_ssl_context()

    assert context.verify_flags != 0xFFFF
    assert context.check_hostname is True
    assert context.verify_mode == 2


def test_httpx_verify_uses_ssl_context() -> None:
    with patch("sse_proxy_python_example.streaming.create_ssl_context") as context_factory:
        assert get_httpx_verify() is context_factory.return_value


@pytest.mark.asyncio
async def test_aiohttp_stream_uses_ssl_context_connector() -> None:
    settings = Settings(api_key=SecretStr("secret"), model="test-model")
    session = MagicMock()
    response = MagicMock()
    response.status = 200
    response.content.iter_any.return_value = empty_async_iterator()
    session.post.return_value.__aenter__.return_value = response

    with (
        patch("sse_proxy_python_example.streaming.aiohttp.ClientSession") as client_session,
        patch("sse_proxy_python_example.streaming.aiohttp.TCPConnector") as connector_factory,
        patch("sse_proxy_python_example.streaming.create_ssl_context") as context_factory,
    ):
        client_session.return_value.__aenter__.return_value = session
        chunks = [chunk async for chunk in stream_aiohttp(settings, {"stream": True})]

    assert chunks == []
    connector_factory.assert_called_once_with(ssl=context_factory.return_value)
    assert client_session.call_args.kwargs["connector"] is connector_factory.return_value


@pytest.mark.asyncio
async def test_openai_sdk_stream_preserves_api_error_message() -> None:
    settings = Settings(api_key=SecretStr("secret"), model="test-model")
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    api_error = APIError("quota exceeded", request, body={"code": "insufficient_quota"})
    client = MagicMock()
    client.responses.create.side_effect = api_error
    client.close = AsyncMock()

    with patch("sse_proxy_python_example.streaming.AsyncOpenAI", return_value=client):
        chunks = [chunk async for chunk in proxy_event_stream(stream_openai_sdk(settings, {}))]

    assert chunks == [b'event: error\ndata: {"error": "quota exceeded"}\n\n']


async def empty_async_iterator() -> AsyncIterator[bytes]:
    if False:
        yield b""
