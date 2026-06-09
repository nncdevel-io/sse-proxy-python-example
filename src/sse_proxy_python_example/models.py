from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sse_proxy_python_example.config import Settings


class ProxyRequest(BaseModel):
    """Request accepted by the proxy endpoints."""

    input: str | list[dict[str, Any]] | dict[str, Any]
    instructions: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: dict[str, Any] | None = None
    json_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    schema_name: str = "response"
    strict_schema: bool = True

    model_config = ConfigDict(populate_by_name=True)

    def to_llm_payload(self, settings: Settings) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": settings.model,
            "input": self.input,
            "stream": True,
        }

        optional_fields = {
            "instructions": self.instructions,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "metadata": self.metadata,
        }
        payload.update({key: value for key, value in optional_fields.items() if value is not None})

        if self.json_schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": self.schema_name,
                    "schema": self.json_schema,
                    "strict": self.strict_schema,
                }
            }

        return payload

