# 📖 sub_api Usage Guide

`sub_api` is a Python package built to let you interact with locally authenticated AI CLI tools effortlessly. Whether you want to use it directly in Python scripts, via the command line, or as an OpenAI-compatible HTTP server, we've got you covered.

## ✅ Requirements

- **Python:** 3.11 or higher
- **Backend CLIs:** At least one of the following installed and authenticated:
  - Gemini CLI: `@google/gemini-cli`
  - Claude Code: `@anthropic-ai/claude-code`
  - Codex CLI: `@openai/codex`

## 📦 Installation

Install the core library directly from GitHub:

```bash
pip install "sub_api @ git+https://github.com/0n1ac/sub_api.git"
```

Install with the FastAPI-based local server:

```bash
pip install "sub_api[server] @ git+https://github.com/0n1ac/sub_api.git"
```

Install with tokenizer-based token estimates:

```bash
pip install "sub_api[tokenizer] @ git+https://github.com/0n1ac/sub_api.git"
```

For local development:

```bash
git clone https://github.com/0n1ac/sub_api.git
cd sub_api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

`sub_api` is not currently published to PyPI, so `pip install sub_api` will not work unless the package is published there later.

*Note: The repository uses a `src/` layout. Imports will still be `import sub_api`.*

## 🔧 Backend CLI Setup

Before `sub_api` can do its magic, make sure you've installed and logged into the CLI tool you want to use.

**For Gemini:**
```bash
npm install -g @google/gemini-cli
gemini auth
```

When running Gemini through `sub_api`, the spawned Gemini CLI process receives `GEMINI_CLI_TRUST_WORKSPACE=true`. This prevents trusted-directory failures in headless or automated environments while keeping the setting local to that subprocess.

**For Claude:**
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

**For Codex:**
```bash
npm install -g @openai/codex
codex login
```

## 🐍 Python Library Usage

Using `sub_api` in your Python code is super straightforward.

**Simple prompt call:**
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

Library mode limits same-backend concurrency to one call by default. This avoids racing against the same CLI session. Raise or disable the limit explicitly when your app can do so safely:

```python
client = SubApiClient(max_concurrent_per_backend=2)     # allow two calls per backend
client = SubApiClient(max_concurrent_per_backend=None)  # disable the library limiter
```

**Call with latency metadata:**
```python
from sub_api import SubApiClient

client = SubApiClient()
result = client.call_result(
    prompt="Hello!",
    backend="gemini",
    model="gemini-2.5-pro",
)

print(result.content)
print(result.latency.as_dict())
print(result.usage.as_openai_usage(), result.usage.source)
```

**OpenAI-style chat completions:**
If you're already used to the OpenAI SDK, you'll feel right at home:
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

**Streaming call:**
```python
stream = client.chat.completions.create(
    model="claude/sonnet",
    messages=[{"role": "user", "content": "Write a short intro."}],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

**Check backend availability:**
```python
from sub_api import SubApiClient

client = SubApiClient()
print(client.is_available("gemini"))
print(client.available_backends())
```

## 💻 Command Line Interface (CLI)

You can also use `sub_api` straight from your terminal!

**Ask a quick question:**
```bash
sub_api ask "Explain decorators in Python." --backend gemini --model gemini-2.5-pro
```

**Print latency and token stats:**
```bash
sub_api ask "Explain decorators in Python." --backend gemini --stats
```

**Stream output:**
```bash
sub_api ask "Write a short intro." --backend claude --stream
sub_api ask "Write a short intro." --backend claude --stream --stats
sub_api ask "Write a short intro." --backend gemini --stream --disable-tools
```

**Pipe content from standard input:**
```bash
echo "Review this code" | sub_api ask --backend claude --model sonnet
```

**Check the status of your installed backends:**
```bash
sub_api status
```

**Check version:**
```bash
sub_api version
```

## 🧪 Testing Scripts

We've included some handy scripts to help you test things out.

**Test a real backend CLI (no server required):**
```bash
python examples/direct_call.py "Hello" --backend gemini --model gemini-2.5-pro
echo "Summarize this" | python examples/direct_call.py --backend claude --model sonnet
python examples/direct_call.py "Hello" --backend gemini --stats
python examples/direct_call.py "Write a short intro" --backend claude --stream
```

**Run a quick smoke test (mocks the backend, no auth needed):**
```bash
python examples/smoke_direct_client.py
```

## 🌐 OpenAI-Compatible Server

You can spin up a local server that mimics the OpenAI API. This is perfect for connecting tools like Cursor, Continue, or Open WebUI.

**Start the server:**
```bash
sub_api serve --host 127.0.0.1 --port 8000
```

**Health check:**
```bash
curl http://127.0.0.1:8000/health
```

**List available models:**
```bash
curl http://127.0.0.1:8000/v1/models
```

**Create a chat completion:**
```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini/gemini-2.5-pro",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

**Streaming API call:**
```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude/sonnet",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

## 🔌 External Tool Configuration

If you're plugging `sub_api` into tools like Cursor, Continue, Open WebUI, or AnythingLLM, use these generic settings:

```text
Base URL: http://localhost:8000/v1
API Key: dummy
Model: gemini/gemini-2.5-pro (or claude/sonnet, codex/gpt-5)
```

## 🚨 Error Handling

If you're integrating `sub_api` into your Python app, you can catch these specific exceptions:

```python
from sub_api import (
    BackendConcurrencyTimeout,
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
    SubApiError,
)
```

When using **Server mode**, expect standard HTTP status codes:
- `400`: Unsupported model or option requested.
- `500`: The backend CLI failed to execute or we couldn't parse its output.
- `503`: The requested backend CLI isn't installed or isn't on your system's `PATH`, or a concurrency slot timed out.
- `504`: The backend CLI took too long and timed out.

## ⚙️ Environment Variables

You can configure default behaviors using a `.env` file:

```env
HOST=127.0.0.1
PORT=8000
TIMEOUT=60
DEFAULT_BACKEND=gemini
SUB_API_SERVER_MAX_CONCURRENT_PER_BACKEND=1
# SUB_API_CONCURRENCY_QUEUE_TIMEOUT=30
# Optional. Omit to use each CLI's native default model.
SUB_API_DEFAULT_MODEL_GEMINI=gemini-2.5-pro
SUB_API_DEFAULT_MODEL_CLAUDE=sonnet
SUB_API_DEFAULT_MODEL_CODEX=gpt-5
# Disable Gemini CLI tools
# SUB_API_GEMINI_DISABLE_TOOLS=true
```

## ⏱️ Latency Stats

`sub_api` records latency stats for each completed backend call.

```json
{
  "sub_api": {
    "backend": "gemini",
    "latency_ms": {
      "total": 2431,
      "queued": 0,
      "spawn": 12,
      "first_stdout": 2180,
      "first_content": 2180,
      "execution": 2120,
      "parse": 131
    }
  }
}
```

- `queued`: time spent waiting for a concurrency slot
- `spawn`: process creation overhead
- `first_stdout`: time until the first stdout event
- `first_content`: time until the first assistant text chunk
- `execution`: process runtime
- `parse`: stdout parsing / JSON decoding time
- `total`: separately measured wall-clock time, not the sum of the other fields

Stage values may be `null` when unavailable.

## 🔒 Concurrency Policy

Server mode uses a process-wide semaphore for calls to the same backend. The default is one in-flight call per backend, which avoids racing against the same authenticated CLI session.

```env
SUB_API_SERVER_MAX_CONCURRENT_PER_BACKEND=1
SUB_API_CONCURRENCY_QUEUE_TIMEOUT=30
```

Library mode also limits same-backend concurrency to one call by default. Use `SubApiClient(max_concurrent_per_backend=N)` to raise the limit, or `SubApiClient(max_concurrent_per_backend=None)` to disable the library limiter. Queue wait time is recorded in `latency_ms.queued`; if the queue timeout is exceeded, `BackendConcurrencyTimeout` is raised.

## 🔢 Token Stats

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

Streaming calls also expose latency and token stats after the stream is exhausted. Token usage may be estimated for streaming responses because some backend streaming formats do not include native usage metadata.

When backend tools are used, `sub_api.tools` and CLI `tools:` stats show the tool names observed in the backend output. For Gemini, set `SUB_API_GEMINI_DISABLE_TOOLS=true` or pass `--disable-tools` in the CLI to disable tool-heavy behavior for a call. Current Gemini CLI versions error when zero tools are configured, so `sub_api` restricts Gemini to a minimal built-in allowlist that prevents search, fetch, file, shell, MCP, extension, and skill tools from being exposed.

## ⚠️ Limitations

A few things to keep in mind:
- Tool/function calling isn't supported.
- Multimodal inputs (like images) aren't supported.
- Token usage is provided, but may be estimated depending on `sub_api.usage.source`.
- Under the hood, array messages are flattened into a single string prompt before hitting the backend CLI.
- Some backend CLIs may emit stdout only after the final answer; in that case streaming falls back to a single final content chunk.
