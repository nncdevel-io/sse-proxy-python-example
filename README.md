# sse-proxy-python-example

Python implementation example of an SSE proxy for streaming API responses.

## Overview

This is a FastAPI-based BFF for proxying streaming LLM API responses. A client
calls this app instead of calling the LLM API directly, and this app forwards the
request to an OpenAI-compatible `/responses` endpoint with the server-side API
key.

Each proxy endpoint uses a different Python upstream client implementation while
accepting the same request body and returning `text/event-stream`.

| Upstream client | Endpoint | What it demonstrates |
| ---- | ---- | ---- |
| OpenAI Python SDK | `/openai-python/responses` | Uses the official SDK and converts SDK stream events back to SSE |
| httpx | `/httpx/responses` | Uses a general-purpose async HTTP client and relays upstream SSE bytes directly |
| aiohttp | `/aiohttp/responses` | Uses aiohttp's async client streaming API and relays upstream SSE bytes directly |

The proxy reads the LLM connection settings on the server side. The API key is
not accepted from the browser request body.

## Getting Started

Install dependencies.

```bash
uv sync
```

Start the proxy with a local OpenAI-compatible server such as Ollama.

```bash
LLM_BASE_URL=http://localhost:11434/v1/ \
LLM_API_KEY=ollama \
LLM_MODEL=llama3.2 \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

Or start it with the OpenAI API.

```bash
LLM_BASE_URL=https://api.openai.com/v1/ \
LLM_API_KEY="$OPENAI_API_KEY" \
LLM_MODEL=gpt-5-mini \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

In another terminal, verify that SSE chunks are streamed.

```bash
curl -N http://127.0.0.1:8000/httpx/responses \
  -H 'Content-Type: application/json' \
  -d '{"input":"Write one short sentence about SSE."}'
```

## Settings

| Environment variable | Default | Description |
| ---- | ---- | ---- |
| `LLM_BASE_URL` | `http://localhost:11434/v1/` | OpenAI-compatible API base URL |
| `LLM_API_KEY` | `ollama` | API key sent to the upstream server |
| `LLM_MODEL` | `llama3.2` | Model name sent to `/responses` |
| `LLM_REQUEST_TIMEOUT` | `120.0` | Upstream request timeout in seconds |
| `LLM_PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | Base URL printed in startup logs |

## Local Run

```bash
uv sync
LLM_BASE_URL=http://localhost:11434/v1/ \
LLM_API_KEY=ollama \
LLM_MODEL=llama3.2 \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

The app listens on <http://127.0.0.1:8000> by default.

## Docker Run

```bash
docker build -t sse-proxy-python-example .
docker run --rm -p 8000:8000 \
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1/ \
  -e LLM_API_KEY=ollama \
  -e LLM_MODEL=llama3.2 \
  sse-proxy-python-example
```

For the OpenAI API, pass your API key through the environment instead of
embedding it in the image.

```bash
docker run --rm -p 8000:8000 \
  -e LLM_BASE_URL=https://api.openai.com/v1/ \
  -e LLM_API_KEY="$OPENAI_API_KEY" \
  -e LLM_MODEL=gpt-5-mini \
  sse-proxy-python-example
```

## Request Examples

Send the same payload to all three endpoints and compare the streamed SSE
output. Use `curl -N` so chunks are printed as they arrive.

```bash
payload='{"input":"Write one short sentence about SSE."}'

curl -N http://127.0.0.1:8000/openai-python/responses \
  -H 'Content-Type: application/json' \
  -d "$payload"

curl -N http://127.0.0.1:8000/httpx/responses \
  -H 'Content-Type: application/json' \
  -d "$payload"

curl -N http://127.0.0.1:8000/aiohttp/responses \
  -H 'Content-Type: application/json' \
  -d "$payload"
```

## Structured Outputs Example

```bash
curl -N http://127.0.0.1:8000/httpx/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "input": "Return a one sentence answer.",
    "schema_name": "answer",
    "schema": {
      "type": "object",
      "properties": {
        "answer": { "type": "string" }
      },
      "required": ["answer"],
      "additionalProperties": false
    }
  }'
```

## Ollama Check

Start an OpenAI-compatible Ollama server, then run the app with:

```bash
LLM_BASE_URL=http://localhost:11434/v1/ \
LLM_API_KEY=ollama \
LLM_MODEL=llama3.2 \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

Then run one of the `curl -N` commands above.

## OpenAI API Check

```bash
LLM_BASE_URL=https://api.openai.com/v1/ \
LLM_API_KEY="$OPENAI_API_KEY" \
LLM_MODEL=gpt-5-mini \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

Then run the same three endpoint requests from the request examples.

## Tests

Normal tests do not call an actual LLM API.

```bash
uv run pytest
uv run ruff check .
uv run pyright
markdownlint-cli2 README.md task.md .markdownlint-cli2.jsonc
```

## Corporate Proxy With Custom CA

Use this setup when the LLM API must be reached through a corporate proxy that
uses a private corporate root CA. The upstream HTTP clients use standard proxy
and Python SSL environment variables.

The app keeps TLS certificate verification enabled. For Python 3.13, it removes
only the stricter X.509 verification flag that can reject some corporate proxy
certificates with errors such as `Missing Authority Key Identifier`.

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export HTTP_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

Export the corporate root CA as a PEM file and point Python/httpx at it with
`SSL_CERT_FILE`. Do not disable TLS verification.

```bash
SSL_CERT_FILE=/path/to/corporate-ca.pem \
LLM_BASE_URL=https://api.openai.com/v1/ \
LLM_API_KEY="$OPENAI_API_KEY" \
LLM_MODEL=gpt-5-mini \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

Use `SSL_CERT_DIR` instead when your environment provides a hashed certificate
directory.

For Docker, mount the CA file and pass the same variables into the container.

```bash
docker run --rm -p 8000:8000 \
  -e LLM_BASE_URL=https://api.openai.com/v1/ \
  -e LLM_API_KEY="$OPENAI_API_KEY" \
  -e LLM_MODEL=gpt-5-mini \
  -e SSL_CERT_FILE=/etc/ssl/certs/corporate-ca.pem \
  -e HTTPS_PROXY \
  -e HTTP_PROXY \
  -e NO_PROXY \
  -v /path/to/corporate-ca.pem:/etc/ssl/certs/corporate-ca.pem:ro \
  sse-proxy-python-example
```

If a request returns `event: error`, check the server log. Upstream connection
exceptions are logged there while the SSE response keeps secret values out of
the client-visible error body.
