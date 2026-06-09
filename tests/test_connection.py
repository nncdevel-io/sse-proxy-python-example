import httpx
import pytest


@pytest.mark.asyncio
async def test_mock_llm_connection_streams_sse() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://llm.example.test/v1/responses"
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b"event: response.output_text.delta\ndata: {\"delta\":\"ok\"}\n\n",
        )

    payload = {
        "model": "test-model",
        "input": "Reply with one short sentence.",
        "stream": True,
    }
    headers = {
        "Authorization": "Bearer test-key",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    transport = httpx.MockTransport(handler)

    async with (
        httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(30.0, read=30.0)) as client,
        client.stream(
            "POST",
            "https://llm.example.test/v1/responses",
            headers=headers,
            json=payload,
        ) as response,
    ):
        assert response.status_code == 200
        body = b"".join([chunk async for chunk in response.aiter_bytes()])

    assert body == b"event: response.output_text.delta\ndata: {\"delta\":\"ok\"}\n\n"
