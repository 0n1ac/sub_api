# 🚀 sub_api

**Turn your AI CLI tools into a lightweight local API.**

`sub_api` lets you call the Gemini CLI, Claude Code, and Codex CLI directly from your Python code, or via an optional **OpenAI-compatible local server**. 

If you already pay for AI subscriptions and use their official CLI tools, `sub_api` helps you integrate them into your own scripts or use them with editors like Cursor and Open WebUI—without needing an extra API key!

> ⚠️ **Note:** This project is intended for personal use with your own authenticated CLI tools. You are responsible for following each provider's terms and usage limits.

## 📖 Table of Contents

- [✨ Features](#-features)
- [📦 Installation](#-installation)
- [🛠️ Prerequisites](#️-prerequisites)
- [🚀 Quick Start](#-quick-start)
- [🔌 Using with External Tools](#-using-with-external-tools)
- [📚 Documentation](#-documentation)
- [⚠️ Current Limitations](#️-current-limitations)
- [📄 License](#-license)

## ✨ Features

- **Library-First:** Direct Python API with no HTTP server required.
- **OpenAI-Compatible:** Drop-in `client.chat.completions.create(...)` interface.
- **Server Mode:** Run a local FastAPI server to use with Cursor, Continue, or Open WebUI.
- **Handy CLI:** Run one-shot prompts, check status, or spin up the server from your terminal.
- **Stateless & Simple:** Just wraps subprocess calls to the official CLIs you already have installed.

## 📦 Installation

Install the core library directly from GitHub:

```bash
pip install "sub_api @ git+https://github.com/0n1ac/sub_api.git"
```

Install with OpenAI-compatible server support:

```bash
pip install "sub_api[server] @ git+https://github.com/0n1ac/sub_api.git"
```

Install with tokenizer-based token estimates:

```bash
pip install "sub_api[tokenizer] @ git+https://github.com/0n1ac/sub_api.git"
```

From source for development:

```bash
git clone https://github.com/0n1ac/sub_api.git
cd sub_api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

`sub_api` is not currently published to PyPI, so `pip install sub_api` will not work unless the package is published there in the future.

## 🛠️ Prerequisites

You need to install and authenticate at least one supported backend CLI on your machine.

| Model | Supported CLI | Example Setup |
|---|---|---|
| `gemini` | Gemini CLI | `npm install -g @google/gemini-cli` <br/> `gemini auth` |
| `claude` | Claude Code | `npm install -g @anthropic-ai/claude-code` <br/> `claude login` |
| `codex` | Codex CLI | `npm install -g @openai/codex` <br/> `codex login` |

For Gemini, `sub_api` sets `GEMINI_CLI_TRUST_WORKSPACE=true` only for the spawned Gemini CLI process. This avoids trusted-directory prompts in headless usage without changing your global shell environment.

## 🚀 Quick Start

### 1. Direct Python Usage

```python
from sub_api import SubApiClient

client = SubApiClient()
answer = client.call(
    prompt="Hello!",
    backend="gemini",
    model="gemini-2.5-pro",  # optional; omit to use the CLI's default model
)
print(answer)
```

Library mode limits same-backend concurrency to one call by default. Raise or disable that limit explicitly when your app can safely run multiple calls against the same CLI session:

```python
client = SubApiClient(max_concurrent_per_backend=2)     # allow two calls per backend
client = SubApiClient(max_concurrent_per_backend=None)  # disable the library limiter
```

Use `call_result(...)` when you also need latency metadata:

```python
result = client.call_result(
    prompt="Hello!",
    backend="gemini",
    model="gemini-2.5-pro",
)

print(result.content)
print(result.latency.as_dict())
print(result.usage.as_openai_usage(), result.usage.source)
```

### 2. OpenAI-Style Interface

```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini/gemini-2.5-pro",
    messages=[{"role": "user", "content": "Hello!"}],
)

print(response.choices[0].message.content)
print(response.sub_api["latency_ms"])
print(response.usage)
print(response.sub_api["usage"]["source"])
```

Streaming uses the same OpenAI-style interface:

```python
stream = client.chat.completions.create(
    model="claude/sonnet",
    messages=[{"role": "user", "content": "Write a short intro."}],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

### 3. Terminal CLI

```bash
# Ask a quick question
sub_api ask "Explain this project in one sentence." --backend gemini --model gemini-2.5-pro

# Pipe input
echo "Summarize this text" | sub_api ask --backend claude --model sonnet

# Print latency stats to stderr
sub_api ask "Hello" --backend gemini --stats

# Stream chunks when the backend exposes stdout incrementally
sub_api ask "Write a short intro." --backend claude --stream
```

### 4. Local API Server

Spin up the server to expose an OpenAI-compatible endpoint:

```bash
sub_api serve --host 127.0.0.1 --port 8000
```

Then call it just like the OpenAI API:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini/gemini-2.5-pro","messages":[{"role":"user","content":"hi"}]}'
```

For Server-Sent Events streaming, pass `"stream": true`:

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"claude/sonnet","stream":true,"messages":[{"role":"user","content":"hi"}]}'
```

## 🔌 Using with External Tools

Want to use your CLI tools with Cursor, Continue, or Open WebUI? Just point them to your local server:

```text
Base URL: http://localhost:8000/v1
API Key: dummy (or anything)
Model: gemini/gemini-2.5-pro (or claude/sonnet, codex/gpt-5)
```

### LangChain Integration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy",
    model="gemini/gemini-2.5-pro",
)
```

### LiteLLM Integration

```python
import litellm

litellm.api_base = "http://localhost:8000/v1"
response = litellm.completion(
    model="openai/gemini/gemini-2.5-pro",
    messages=[{"role": "user", "content": "hi"}],
)
```

## 📚 Documentation

For more details, check out the full guides:
- [Usage Guide (English)](docs/USAGE.en.md)
- [사용법 문서 (Korean)](docs/USAGE.ko.md)

## ⚠️ Current Limitations

- No tool/function calling
- Token usage may be estimated depending on `sub_api.usage.source`
- Message arrays are serialized into a single prompt string under the hood
- CLI output formats might break if upstream tools change their output structure
- Some backend CLIs may emit stdout only after the final answer; in that case streaming falls back to a single final content chunk

## Latency Stats

OpenAI-style responses include `sub_api.latency_ms`:

```json
{
  "sub_api": {
    "backend": "gemini",
    "latency_ms": {
      "total": 2431,
      "queued": 0,
      "spawn": 12,
      "first_stdout": 2180,
      "execution": 2120,
      "parse": 131
    }
  }
}
```

`queued` measures time spent waiting for a concurrency slot, `spawn` measures process creation overhead, `first_stdout` measures time until the first stdout byte, `execution` measures process runtime, and `parse` measures output parsing time. `total` is measured separately as wall-clock time. Stage values may be `null` if a stage cannot be measured.

## Concurrency Policy

Server mode limits concurrent calls per backend with a shared semaphore. The default is one in-flight call per backend, which avoids racing against the same authenticated CLI session. Configure it with `SUB_API_SERVER_MAX_CONCURRENT_PER_BACKEND`.

Library mode also limits same-backend concurrency to one call by default. Use `SubApiClient(max_concurrent_per_backend=N)` to raise the limit, or `SubApiClient(max_concurrent_per_backend=None)` to disable the library limiter. Requests that wait for a slot are reflected in `sub_api.latency_ms.queued`; requests that exceed the queue timeout raise `BackendConcurrencyTimeout` or return HTTP 503 in server mode.

## Token Stats

OpenAI-style responses include the standard `usage` object. The reliability of those numbers is exposed separately through `sub_api.usage.source`.

```json
{
  "usage": {
    "prompt_tokens": 142,
    "completion_tokens": 318,
    "total_tokens": 460
  },
  "sub_api": {
    "usage": {
      "source": "heuristic"
    }
  }
}
```

Possible sources:

- `native`: the backend CLI provided token usage directly
- `tiktoken_estimate`: estimated with optional `tiktoken`
- `heuristic`: fallback estimate, currently length-based

## 📄 License

MIT
