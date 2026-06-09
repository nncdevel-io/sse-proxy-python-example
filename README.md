# sse-proxy-python-example

ストリーミング API レスポンスを SSE として中継する Python 実装例です。

## 概要

このアプリは、ストリーミング LLM API レスポンスを中継する FastAPI ベースの
BFF です。クライアントは LLM API を直接呼び出さず、このアプリを呼び出します。
このアプリはサーバー側に保持した API key を使って、OpenAI 互換の
`/responses` endpoint へリクエストを転送します。

3つの proxy endpoint は同じ request body を受け取り、いずれも
`text/event-stream` を返します。違いは、上流 LLM API を呼び出す Python
client の実装です。

| 上流 client | Endpoint | 確認できること |
| ---- | ---- | ---- |
| OpenAI Python SDK | `/openai-python/responses` | 公式 SDK の stream event を SSE に戻す実装 |
| httpx | `/httpx/responses` | 汎用 async HTTP client で上流 SSE bytes をそのまま中継する実装 |
| aiohttp | `/aiohttp/responses` | aiohttp の async client streaming API で上流 SSE bytes をそのまま中継する実装 |

LLM 接続設定はサーバー側の環境変数から読みます。ブラウザや request body から
API key は受け取りません。

## はじめかた

依存関係をインストールします。

```bash
uv sync
```

Ollama などのローカル OpenAI 互換 server を使う場合は、次のように起動します。

```bash
LLM_BASE_URL=http://localhost:11434/v1/ \
LLM_API_KEY=ollama \
LLM_MODEL=llama3.2 \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

OpenAI API を使う場合は、次のように起動します。

```bash
LLM_BASE_URL=https://api.openai.com/v1/ \
LLM_API_KEY="$OPENAI_API_KEY" \
LLM_MODEL=gpt-5-mini \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

別の terminal から SSE chunk が流れることを確認します。

```bash
curl -N http://127.0.0.1:8000/httpx/responses \
  -H 'Content-Type: application/json' \
  -d '{"input":"Write one short sentence about SSE."}'
```

## 設定

| 環境変数 | 既定値 | 説明 |
| ---- | ---- | ---- |
| `LLM_BASE_URL` | `http://localhost:11434/v1/` | OpenAI 互換 API の base URL |
| `LLM_API_KEY` | `ollama` | 上流 server へ送る API key |
| `LLM_MODEL` | `llama3.2` | `/responses` へ送る model 名 |
| `LLM_REQUEST_TIMEOUT` | `120.0` | 上流 request timeout 秒数 |
| `LLM_PUBLIC_BASE_URL` | `http://127.0.0.1:8000` | 起動ログに表示する公開 base URL |

## ローカル起動

```bash
uv sync
LLM_BASE_URL=http://localhost:11434/v1/ \
LLM_API_KEY=ollama \
LLM_MODEL=llama3.2 \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

既定では <http://127.0.0.1:8000> で待ち受けます。

## Docker 起動

```bash
docker build -t sse-proxy-python-example .
docker run --rm -p 8000:8000 \
  -e LLM_BASE_URL=http://host.docker.internal:11434/v1/ \
  -e LLM_API_KEY=ollama \
  -e LLM_MODEL=llama3.2 \
  sse-proxy-python-example
```

OpenAI API を使う場合は、API key を image に埋め込まず、環境変数として渡します。

```bash
docker run --rm -p 8000:8000 \
  -e LLM_BASE_URL=https://api.openai.com/v1/ \
  -e LLM_API_KEY="$OPENAI_API_KEY" \
  -e LLM_MODEL=gpt-5-mini \
  sse-proxy-python-example
```

## Request 例

同じ payload を3つの endpoint に投げて、SSE の出力を比較できます。
`curl -N` を使うと chunk が到着したタイミングで逐次表示されます。

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

## Structured Outputs 例

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

## Ollama 確認

OpenAI 互換 API として動く Ollama server を起動してから、このアプリを起動します。

```bash
LLM_BASE_URL=http://localhost:11434/v1/ \
LLM_API_KEY=ollama \
LLM_MODEL=llama3.2 \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

起動後、上記の `curl -N` コマンドを実行します。

## OpenAI API 確認

```bash
LLM_BASE_URL=https://api.openai.com/v1/ \
LLM_API_KEY="$OPENAI_API_KEY" \
LLM_MODEL=gpt-5-mini \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

起動後、Request 例の3つの endpoint を同じ payload で確認します。

## テスト

通常のテストでは実際の LLM API を呼びません。

```bash
uv run pytest
uv run ruff check .
uv run pyright
markdownlint-cli2 README.md task.md .markdownlint-cli2.jsonc
```

## 独自 CA を使う社内プロキシ配下での起動

LLM API へ到達するために社内プロキシを経由する必要があり、そのプロキシが
社内独自の root CA を使う場合は、この手順で起動します。上流 HTTP client は
標準の proxy 環境変数と Python SSL 環境変数を使います。

このアプリは TLS 証明書検証を有効にしたまま動作します。Python 3.13 では、
`Missing Authority Key Identifier` などのエラーで一部の社内プロキシ証明書が
拒否されることがあります。そのため、このアプリは Python 3.13 の厳格な
X.509 検証 flag だけを外し、証明書検証自体は維持します。

proxy の環境変数を設定します。

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export HTTP_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

社内 root CA を PEM file として用意し、Python/httpx が読む `SSL_CERT_FILE`
に指定します。

```bash
SSL_CERT_FILE=/path/to/corporate-ca.pem \
LLM_BASE_URL=https://api.openai.com/v1/ \
LLM_API_KEY="$OPENAI_API_KEY" \
LLM_MODEL=gpt-5-mini \
uv run uvicorn sse_proxy_python_example.app:app --reload
```

証明書が hashed certificate directory として提供される環境では、
`SSL_CERT_DIR` を使います。

Docker では CA file を container に mount し、同じ環境変数を渡します。

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

起動ログには `SSL_CERT_FILE` のパスが表示されます。`event: error` が返る場合は
server log を確認してください。上流接続の例外は server log に出力し、client
向けの SSE error body には API key や proxy 認証情報を出しません。
