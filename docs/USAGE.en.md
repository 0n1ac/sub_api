# sub_api Usage Guide

`sub_api` is a library-first Python package for calling your locally authenticated AI CLI tools. You can use it directly from Python, from the `sub_api` command line tool, or through the optional OpenAI-compatible HTTP server.

## Requirements

- Python 3.11+
- At least one installed and authenticated backend CLI:
  - Gemini CLI: `@google/gemini-cli`
  - Claude Code: `@anthropic-ai/claude-code`
  - Codex CLI: `@openai/codex`

## Installation

Core library:

```bash
pip install sub_api
```

Core library plus server mode:

```bash
pip install "sub_api[server]"
```

Local development checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

The repository uses a `src/` layout. After editable installation, imports still use `sub_api`.

## Backend CLI Setup

Install and log in to the backend CLI you want to use.

```bash
npm install -g @google/gemini-cli
gemini auth
```

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

```bash
npm install -g @openai/codex
codex login
```

## Python Library Usage

Simple prompt call:

```python
from sub_api import SubApiClient

client = SubApiClient()
answer = client.call(model="gemini", prompt="Hello")
print(answer)
```

OpenAI-style chat completions:

```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini",
    messages=[{"role": "user", "content": "Hello"}],
)

print(response.choices[0].message.content)
```

Check backend availability:

```python
from sub_api import SubApiClient

client = SubApiClient()
print(client.is_available("gemini"))
print(client.available_backends())
```

## CLI Usage

Ask a one-shot question:

```bash
sub_api ask "Explain decorators in Python." --model gemini
```

Read the prompt from stdin:

```bash
echo "Review this code" | sub_api ask --model claude
```

Show backend status:

```bash
sub_api status
```

Show package version:

```bash
sub_api version
```

## Direct-Call Test Scripts

Call a real backend CLI without starting the server:

```bash
python examples/direct_call.py "Hello" --model gemini
echo "Summarize this" | python examples/direct_call.py --model claude
```

Run a fast smoke test that does not require backend CLI authentication:

```bash
python examples/smoke_direct_client.py
```

## OpenAI-Compatible Server

Install server dependencies and start the server:

```bash
pip install "sub_api[server]"
sub_api serve --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

List available models:

```bash
curl http://127.0.0.1:8000/v1/models
```

Create a chat completion:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

## External Tool Configuration

Use these values in tools such as Cursor, Continue, Open WebUI, or AnythingLLM:

```text
Base URL: http://localhost:8000/v1
API Key: dummy
Model: gemini
```

## Error Handling

When using the Python library, catch these exceptions:

```python
from sub_api import (
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
    SubApiError,
)
```

Server mode uses these common HTTP statuses:

- `400`: unsupported model or unsupported option
- `503`: backend CLI is not installed or not available on `PATH`
- `504`: backend CLI timed out
- `500`: backend CLI execution or output parsing failed

## Environment Variables

You can place these values in `.env`:

```env
HOST=127.0.0.1
PORT=8000
TIMEOUT=60
DEFAULT_BACKEND=gemini
```

## Limitations

- Streaming is not implemented
- Tool/function calling is not implemented
- Multimodal inputs are not implemented
- Token usage is not calculated
- Messages are serialized into a single prompt string before being sent to the backend CLI
