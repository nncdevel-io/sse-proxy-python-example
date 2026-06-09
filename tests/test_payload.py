from pydantic import SecretStr

from sse_proxy_python_example.config import Settings
from sse_proxy_python_example.models import ProxyRequest


def test_text_request_builds_streaming_responses_payload() -> None:
    request = ProxyRequest(input="hello")
    settings = Settings(model="test-model", api_key=SecretStr("secret"))

    payload = request.to_llm_payload(settings)

    assert payload == {
        "model": "test-model",
        "input": "hello",
        "stream": True,
    }


def test_json_schema_request_adds_structured_outputs_format() -> None:
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    request = ProxyRequest(input="hello", schema=schema, schema_name="answer")
    settings = Settings(model="test-model", api_key=SecretStr("secret"))

    payload = request.to_llm_payload(settings)

    assert payload["stream"] is True
    assert payload["text"] == {
        "format": {
            "type": "json_schema",
            "name": "answer",
            "schema": schema,
            "strict": True,
        }
    }
