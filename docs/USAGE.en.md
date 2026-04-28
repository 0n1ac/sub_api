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
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
    SubApiError,
)
```

When using **Server mode**, expect standard HTTP status codes:
- `400`: Unsupported model or option requested.
- `500`: The backend CLI failed to execute or we couldn't parse its output.
- `503`: The requested backend CLI isn't installed or isn't on your system's `PATH`.
- `504`: The backend CLI took too long and timed out.

## ⚙️ Environment Variables

You can configure default behaviors using a `.env` file:

```env
HOST=127.0.0.1
PORT=8000
TIMEOUT=60
DEFAULT_BACKEND=gemini
# Optional. Omit to use each CLI's native default model.
SUB_API_DEFAULT_MODEL_GEMINI=gemini-2.5-pro
SUB_API_DEFAULT_MODEL_CLAUDE=sonnet
SUB_API_DEFAULT_MODEL_CODEX=gpt-5
```

## ⚠️ Limitations

A few things to keep in mind:
- Streaming responses aren't supported yet.
- Tool/function calling isn't supported.
- Multimodal inputs (like images) aren't supported.
- Token usage isn't tracked or calculated.
- Under the hood, array messages are flattened into a single string prompt before hitting the backend CLI.
