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
answer = client.call(model="gemini", prompt="안녕!")
print(answer)
```

**OpenAI 스타일의 chat completions 호출:**
OpenAI SDK 사용 경험이 있다면 아주 익숙하실 겁니다!
```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini",
    messages=[{"role": "user", "content": "안녕!"}],
)

print(response.choices[0].message.content)
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
sub_api ask "Python 데코레이터를 설명해줘." --model gemini
```

**stdin(표준 입력)으로 프롬프트 넘기기:**
```bash
echo "이 코드를 리뷰해줘" | sub_api ask --model claude
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
python examples/direct_call.py "안녕" --model gemini
echo "간단히 요약해줘" | python examples/direct_call.py --model claude
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
    "model": "gemini",
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
Model: gemini (혹은 claude, codex)
```

## 🚨 에러 처리 방법

Python 앱 내에서 `sub_api`를 호출할 때 발생하는 예외 상황을 처리하려면 아래 클래스들을 사용할 수 있습니다.

```python
from sub_api import (
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
    SubApiError,
)
```

**서버 모드** 실행 중에는 일반적인 HTTP 상태 코드가 반환됩니다.
- `400`: 지원하지 않는 모델이거나 잘못된 옵션 요청.
- `500`: 백엔드 CLI 실행에 실패했거나 출력 결과를 파싱하지 못함.
- `503`: 요청한 백엔드 CLI가 설치되어 있지 않거나 `PATH` 환경 변수에서 찾을 수 없음.
- `504`: 백엔드 CLI가 응답하지 않고 타임아웃 발생.

## ⚙️ 환경 변수 설정

`.env` 파일을 만들어 아래와 같이 기본값을 설정할 수 있습니다.

```env
HOST=127.0.0.1
PORT=8000
TIMEOUT=60
DEFAULT_BACKEND=gemini
```

## ⚠️ 현재 제한 사항

사용 시 참고해 주세요:
- 텍스트 스트리밍(Streaming)은 아직 지원하지 않습니다.
- 함수 호출(Tool/Function calling)은 지원하지 않습니다.
- 이미지 등 멀티모달(Multimodal) 입력은 불가능합니다.
- 토큰 사용량 계산 기능은 포함되어 있지 않습니다.
- 백엔드 CLI로 전달될 때 배열 형태의 메시지 이력이 내부적으로 하나의 긴 텍스트 프롬프트로 병합됩니다.
