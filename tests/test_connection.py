import os

import httpx
import pytest


@pytest.mark.asyncio
async def test_optional_llm_connection_streams_sse_when_environment_is_set() -> None:
    base_url = os.getenv("LLM_CONNECTION_TEST_BASE_URL")
    api_key = os.getenv("LLM_CONNECTION_TEST_API_KEY", "ollama")
    model = os.getenv("LLM_CONNECTION_TEST_MODEL")

    if base_url is None or model is None:
        pytest.skip("LLM_CONNECTION_TEST_BASE_URL and LLM_CONNECTION_TEST_MODEL are not set")

    payload = {
        "model": model,
        "input": "Reply with one short sentence.",
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    async with (
        httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=30.0)) as client,
        client.stream(
            "POST",
            base_url.rstrip("/") + "/responses",
            headers=headers,
            json=payload,
        ) as response,
    ):
        assert response.status_code < 300
        first_chunk = await response.aiter_bytes().__anext__()

    assert first_chunk
