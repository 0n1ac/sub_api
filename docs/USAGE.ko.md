# 📖 sub_api 사용 가이드

`sub_api`는 로컬에 인증된 AI CLI 도구를 Python이나 외부 앱에서 손쉽게 호출할 수 있도록 도와주는 라이브러리입니다. 별도의 서버 없이 Python 코드 내에서 직접 사용할 수도 있고, Cursor나 Open WebUI처럼 OpenAI 호환 API가 필요한 도구를 위해 로컬 HTTP 서버를 띄울 수도 있습니다.

## ✅ 요구 사항

- **Python:** 3.11 이상
- **백엔드 CLI:** 다음 중 설치 및 인증이 완료된 도구 하나 이상 필요:
  - Gemini CLI: `@google/gemini-cli`
  - Claude Code: `@anthropic-ai/claude-code`
  - Codex CLI: `@openai/codex`

## 📦 설치 방법

GitHub에서 라이브러리 기능만 설치하려면:

```bash
pip install "sub_api @ git+https://github.com/0n1ac/sub_api.git"
```

FastAPI 기반의 로컬 서버 기능까지 포함해 설치하려면:

```bash
pip install "sub_api[server] @ git+https://github.com/0n1ac/sub_api.git"
```

tokenizer 기반 토큰 추정 기능까지 포함해 설치하려면:

```bash
pip install "sub_api[tokenizer] @ git+https://github.com/0n1ac/sub_api.git"
```

로컬 개발 환경을 세팅하려면:

```bash
git clone https://github.com/0n1ac/sub_api.git
cd sub_api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

현재 `sub_api`는 PyPI에 배포하지 않습니다. 따라서 향후 PyPI에 배포하기 전까지는 `pip install sub_api` 명령으로 설치할 수 없습니다.

*참고: 이 프로젝트는 `src/` 레이아웃을 사용합니다. `editable` 설치 후에도 `import sub_api` 형식으로 사용하시면 됩니다.*

## 🔧 백엔드 CLI 초기 설정

`sub_api`가 백엔드 도구를 호출할 수 있도록, 먼저 원하는 CLI를 설치하고 로그인(인증)을 완료해주세요.

**Gemini 설정:**
```bash
npm install -g @google/gemini-cli
gemini auth
```

`sub_api`를 통해 Gemini를 실행할 때는 Gemini CLI subprocess에만 `GEMINI_CLI_TRUST_WORKSPACE=true` 환경 변수를 전달합니다. 그래서 headless 또는 자동화 환경에서 trusted directory 오류가 나지 않도록 처리하면서, 사용자의 전역 셸 환경은 바꾸지 않습니다.

**Claude 설정:**
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

**Codex 설정:**
```bash
npm install -g @openai/codex
codex login
```

## 🐍 Python 라이브러리로 사용하기

Python 코드 안에서 아주 직관적으로 사용할 수 있습니다.

**간단한 단일 프롬프트 호출:**
```python
from sub_api import SubApiClient

client = SubApiClient()
answer = client.call(
    prompt="안녕!",
    backend="gemini",
    model="gemini-2.5-pro",  # 선택 사항. 생략하면 CLI 기본 모델 사용
)
print(answer)
```

라이브러리 모드는 기본적으로 같은 backend 동시 실행을 1개로 제한합니다. 같은 CLI 세션을 동시에 여러 번 건드리며 생길 수 있는 충돌을 피하기 위한 기본값입니다. 필요하다면 제한을 올리거나 끌 수 있습니다.

```python
client = SubApiClient(max_concurrent_per_backend=2)     # backend별 2개까지 허용
client = SubApiClient(max_concurrent_per_backend=None)  # 라이브러리 limiter 비활성화
```

**latency metadata 포함 호출:**
```python
from sub_api import SubApiClient

client = SubApiClient()
result = client.call_result(
    prompt="안녕!",
    backend="gemini",
    model="gemini-2.5-pro",
)

print(result.content)
print(result.latency.as_dict())
print(result.usage.as_openai_usage(), result.usage.source)
```

**OpenAI 스타일의 chat completions 호출:**
OpenAI SDK 사용 경험이 있다면 아주 익숙하실 겁니다!
```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini/gemini-2.5-pro",
    messages=[{"role": "user", "content": "안녕!"}],
)

print(response.choices[0].message.content)
print(response.sub_api["latency_ms"])
print(response.usage)
print(response.sub_api["usage"]["source"])
```

**Streaming 호출:**
```python
stream = client.chat.completions.create(
    model="claude/sonnet",
    messages=[{"role": "user", "content": "짧은 소개 문장을 써줘."}],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

**백엔드 도구 사용 가능 여부 확인:**
```python
from sub_api import SubApiClient

client = SubApiClient()
print(client.is_available("gemini"))
print(client.available_backends())
```

## 💻 CLI (명령어 도구) 사용법

터미널에서도 `sub_api` 명령어를 바로 쓸 수 있습니다.

**간단한 질문 던지기:**
```bash
sub_api ask "Python 데코레이터를 설명해줘." --backend gemini --model gemini-2.5-pro
```

**latency와 token stats 함께 출력:**
```bash
sub_api ask "Python 데코레이터를 설명해줘." --backend gemini --stats
```

**streaming 출력:**
```bash
sub_api ask "짧은 소개 문장을 써줘." --backend claude --stream
sub_api ask "짧은 소개 문장을 써줘." --backend claude --stream --stats
sub_api ask "짧은 소개 문장을 써줘." --backend gemini --stream --disable-tools
```

**stdin(표준 입력)으로 프롬프트 넘기기:**
```bash
echo "이 코드를 리뷰해줘" | sub_api ask --backend claude --model sonnet
```

**설치된 백엔드 상태 확인:**
```bash
sub_api status
```

**버전 확인:**
```bash
sub_api version
```

## 🧪 테스트 스크립트

개발 및 테스트를 위해 몇 가지 유용한 스크립트가 포함되어 있습니다.

**서버 없이 백엔드 CLI 직접 호출 테스트:**
```bash
python examples/direct_call.py "안녕" --backend gemini --model gemini-2.5-pro
echo "간단히 요약해줘" | python examples/direct_call.py --backend claude --model sonnet
python examples/direct_call.py "안녕" --backend gemini --stats
python examples/direct_call.py "짧은 소개 문장을 써줘" --backend claude --stream
```

**간단한 스모크 테스트 (인증 불필요, mock 사용):**
```bash
python examples/smoke_direct_client.py
```

## 🌐 OpenAI 호환 로컬 서버 실행

Cursor, Continue, Open WebUI 같은 외부 도구와 연동하고 싶을 때 OpenAI 호환 API 서버를 띄울 수 있습니다.

**서버 실행:**
```bash
sub_api serve --host 127.0.0.1 --port 8000
```

**상태 확인 (Health check):**
```bash
curl http://127.0.0.1:8000/health
```

**사용 가능한 모델 목록 조회:**
```bash
curl http://127.0.0.1:8000/v1/models
```

**Chat Completions API 호출:**
```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini/gemini-2.5-pro",
    "messages": [
      {"role": "user", "content": "안녕!"}
    ]
  }'
```

**Streaming API 호출:**
```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude/sonnet",
    "stream": true,
    "messages": [
      {"role": "user", "content": "안녕!"}
    ]
  }'
```

## 🔌 외부 도구 연동 설정

Cursor, Continue, Open WebUI, AnythingLLM 등에서 아래와 같이 설정하면 바로 사용할 수 있습니다.

```text
Base URL: http://localhost:8000/v1
API Key: dummy (아무 값이나 무방)
Model: gemini/gemini-2.5-pro (또는 claude/sonnet, codex/gpt-5)
```

## 🚨 에러 처리 방법

Python 앱 내에서 `sub_api`를 호출할 때 발생하는 예외 상황을 처리하려면 아래 클래스들을 사용할 수 있습니다.

```python
from sub_api import (
    BackendConcurrencyTimeout,
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
    SubApiError,
)
```

**서버 모드** 실행 중에는 일반적인 HTTP 상태 코드가 반환됩니다.
- `400`: 지원하지 않는 모델이거나 잘못된 옵션 요청.
- `500`: 백엔드 CLI 실행에 실패했거나 출력 결과를 파싱하지 못함.
- `503`: 요청한 백엔드 CLI가 설치되어 있지 않거나 `PATH` 환경 변수에서 찾을 수 없음. 또는 concurrency slot 대기 시간이 초과됨.
- `504`: 백엔드 CLI가 응답하지 않고 타임아웃 발생.

## ⚙️ 환경 변수 설정

`.env` 파일을 만들어 아래와 같이 기본값을 설정할 수 있습니다.

```env
HOST=127.0.0.1
PORT=8000
TIMEOUT=60
DEFAULT_BACKEND=gemini
SUB_API_SERVER_MAX_CONCURRENT_PER_BACKEND=1
# SUB_API_CONCURRENCY_QUEUE_TIMEOUT=30
# 선택 사항. 생략하면 각 CLI의 native default 모델 사용
SUB_API_DEFAULT_MODEL_GEMINI=gemini-2.5-pro
SUB_API_DEFAULT_MODEL_CLAUDE=sonnet
SUB_API_DEFAULT_MODEL_CODEX=gpt-5
# Gemini CLI tool 사용 비활성화
# SUB_API_GEMINI_DISABLE_TOOLS=true
```

## ⏱️ Latency Stats

`sub_api`는 완료된 백엔드 호출마다 latency stats를 기록합니다.

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

- `queued`: concurrency slot을 기다린 시간
- `spawn`: 프로세스 생성 오버헤드
- `first_stdout`: 첫 stdout event가 나오기까지 걸린 시간
- `first_content`: 첫 assistant text chunk가 나오기까지 걸린 시간
- `execution`: 프로세스 실행 시간
- `parse`: stdout 파싱 / JSON 디코딩 시간
- `total`: 별도로 측정한 wall-clock 시간이며, 나머지 필드의 합이 아닙니다.

각 단계 값은 측정할 수 없는 경우 `null`일 수 있습니다.

## 🔒 Concurrency Policy

서버 모드는 같은 backend를 동시에 호출할 때 프로세스 전체에서 공유되는 semaphore를 사용합니다. 기본값은 backend별 동시 실행 1개입니다. 같은 계정의 같은 CLI 세션을 동시에 건드리며 생길 수 있는 race condition을 줄이기 위한 기본값입니다.

```env
SUB_API_SERVER_MAX_CONCURRENT_PER_BACKEND=1
SUB_API_CONCURRENCY_QUEUE_TIMEOUT=30
```

라이브러리 모드도 기본적으로 backend별 동시 실행 1개를 적용합니다. 필요하다면 `SubApiClient(max_concurrent_per_backend=N)`으로 제한을 올리거나, `SubApiClient(max_concurrent_per_backend=None)`으로 라이브러리 limiter를 끌 수 있습니다. 대기 시간은 `latency_ms.queued`에 기록되며, queue timeout을 넘기면 `BackendConcurrencyTimeout`이 발생합니다.

## 🔢 Token Stats

OpenAI-style 응답에는 표준 `usage` 객체가 포함됩니다. 이 숫자의 신뢰도는 별도의 `sub_api.usage.source` 필드로 표시합니다.

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

가능한 source 값:

- `native`: 백엔드 CLI가 token usage를 직접 제공한 값
- `tiktoken_estimate`: optional `tiktoken`으로 추정한 값
- `heuristic`: fallback 추정값. 현재는 길이 기반입니다.

Streaming 호출도 stream이 끝난 뒤 latency와 token stats를 제공합니다. 다만 일부 백엔드의 streaming 출력에는 native usage metadata가 포함되지 않을 수 있어 token usage가 추정치로 표시될 수 있습니다.

Backend tool을 사용한 경우 `sub_api.tools`와 CLI의 `tools:` stats에 감지된 tool 이름이 표시됩니다. Gemini는 `SUB_API_GEMINI_DISABLE_TOOLS=true` 또는 CLI의 `--disable-tools` 옵션으로 tool 사용을 끌 수 있습니다.

## ⚠️ 현재 제한 사항

사용 시 참고해 주세요:
- 함수 호출(Tool/Function calling)은 지원하지 않습니다.
- 이미지 등 멀티모달(Multimodal) 입력은 불가능합니다.
- 토큰 사용량은 제공되지만, `sub_api.usage.source`에 따라 추정치일 수 있습니다.
- 백엔드 CLI로 전달될 때 배열 형태의 메시지 이력이 내부적으로 하나의 긴 텍스트 프롬프트로 병합됩니다.
- 일부 백엔드 CLI는 최종 답변 전까지 stdout을 내보내지 않을 수 있습니다. 이 경우 streaming은 최종 응답 1회 chunk로 fallback됩니다.
