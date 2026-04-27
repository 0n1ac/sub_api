# sub_api

Use your AI subscription CLIs as a lightweight local API.

`sub_api` lets personal users call Gemini CLI, Claude Code, and Codex CLI from Python code or through an optional OpenAI-compatible local server. The core package is library-first: you can import it directly without running a web server. Server mode is available when you need compatibility with tools that expect an OpenAI-style `/v1/chat/completions` endpoint.

> This project is intended for personal use with your own authenticated CLI tools. You are responsible for following each provider's terms and usage limits.

## Features

- Direct Python API with no HTTP server required
- OpenAI-style `client.chat.completions.create(...)` interface
- Optional OpenAI-compatible FastAPI server
- CLI commands for one-shot prompts, status checks, and server mode
- Stateless subprocess calls to Gemini, Claude, and Codex CLIs

## Installation

Core library only:

```bash
pip install sub_api
```

With OpenAI-compatible server support:

```bash
pip install "sub_api[server]"
```

From a local checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

This project uses the standard `src/` layout. The import package is still `sub_api`.

## Prerequisites

Install and authenticate at least one supported backend CLI yourself.

| Model | CLI | Example setup |
|---|---|---|
| `gemini` | Gemini CLI | `npm install -g @google/gemini-cli` then `gemini auth` |
| `claude` | Claude Code | `npm install -g @anthropic-ai/claude-code` then `claude login` |
| `codex` | Codex CLI | `npm install -g @openai/codex` then `codex login` |

## Quick Start

Use it directly from Python:

```python
from sub_api import SubApiClient

client = SubApiClient()
answer = client.call(model="gemini", prompt="Hello")
print(answer)
```

Use the OpenAI-style interface:

```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini",
    messages=[{"role": "user", "content": "Hello"}],
)

print(response.choices[0].message.content)
```

Run a one-shot prompt from the shell:

```bash
sub_api ask "Explain this project in one sentence." --model gemini
```

Run the optional OpenAI-compatible server:

```bash
sub_api serve --host 127.0.0.1 --port 8000
```

Then call it with an OpenAI-compatible client:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini","messages":[{"role":"user","content":"hi"}]}'
```

## External Tool Setup

For Cursor, Continue, Open WebUI, or similar tools:

```text
Base URL: http://localhost:8000/v1
API Key: dummy
Model: gemini
```

LangChain example:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy",
    model="gemini",
)
```

LiteLLM example:

```python
import litellm

litellm.api_base = "http://localhost:8000/v1"
response = litellm.completion(
    model="openai/gemini",
    messages=[{"role": "user", "content": "hi"}],
)
```

## CLI

```bash
sub_api ask "Hello" --model gemini
echo "Summarize this" | sub_api ask --model claude
sub_api status
sub_api serve --port 8000
sub_api version
```

## Documentation

- [Usage Guide](docs/USAGE.en.md)
- [사용법 문서](docs/USAGE.ko.md)

## Current Limitations

- No streaming responses yet
- No tool/function calling yet
- No token usage accounting
- Message arrays are serialized into a single prompt string
- CLI output formats may change across upstream CLI versions

## License

MIT
