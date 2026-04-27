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
answer = client.call(model="gemini", prompt="Hello!")
print(answer)
```

### 2. OpenAI-Style Interface

```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini",
    messages=[{"role": "user", "content": "Hello!"}],
)

print(response.choices[0].message.content)
```

### 3. Terminal CLI

```bash
# Ask a quick question
sub_api ask "Explain this project in one sentence." --model gemini

# Pipe input
echo "Summarize this text" | sub_api ask --model claude
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
  -d '{"model":"gemini","messages":[{"role":"user","content":"hi"}]}'
```

## 🔌 Using with External Tools

Want to use your CLI tools with Cursor, Continue, or Open WebUI? Just point them to your local server:

```text
Base URL: http://localhost:8000/v1
API Key: dummy (or anything)
Model: gemini (or claude, codex)
```

### LangChain Integration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy",
    model="gemini",
)
```

### LiteLLM Integration

```python
import litellm

litellm.api_base = "http://localhost:8000/v1"
response = litellm.completion(
    model="openai/gemini",
    messages=[{"role": "user", "content": "hi"}],
)
```

## 📚 Documentation

For more details, check out the full guides:
- [Usage Guide (English)](docs/USAGE.en.md)
- [사용법 문서 (Korean)](docs/USAGE.ko.md)

## ⚠️ Current Limitations

- No streaming responses (yet)
- No tool/function calling
- No token usage accounting
- Message arrays are serialized into a single prompt string under the hood
- CLI output formats might break if upstream tools change their output structure

## 📄 License

MIT
