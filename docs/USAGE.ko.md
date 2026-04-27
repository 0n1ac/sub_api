# sub_api 사용법

`sub_api`는 로컬에 인증된 AI CLI 도구를 Python에서 직접 호출하기 위한 라이브러리 우선 패키지입니다. 서버 없이 Python 코드에서 바로 사용할 수 있고, OpenAI 호환 API가 필요한 외부 도구를 위해 선택적으로 HTTP 서버를 실행할 수 있습니다.

## 요구 사항

- Python 3.11 이상
- 설치 및 인증이 끝난 백엔드 CLI 하나 이상:
  - Gemini CLI: `@google/gemini-cli`
  - Claude Code: `@anthropic-ai/claude-code`
  - Codex CLI: `@openai/codex`

## 설치

라이브러리만 설치:

```bash
pip install sub_api
```

서버 모드까지 설치:

```bash
pip install "sub_api[server]"
```

로컬 개발 체크아웃에서 설치:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"
```

이 저장소는 `src/` 레이아웃을 사용합니다. editable 설치 후 import 이름은 그대로 `sub_api`입니다.

## 백엔드 CLI 설정

사용할 CLI를 직접 설치하고 로그인해야 합니다.

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

## Python 라이브러리 사용

가장 단순한 단일 프롬프트 호출:

```python
from sub_api import SubApiClient

client = SubApiClient()
answer = client.call(model="gemini", prompt="안녕")
print(answer)
```

OpenAI 스타일 chat completions 호출:

```python
from sub_api import SubApiClient

client = SubApiClient()
response = client.chat.completions.create(
    model="gemini",
    messages=[{"role": "user", "content": "안녕"}],
)

print(response.choices[0].message.content)
```

백엔드 사용 가능 여부 확인:

```python
from sub_api import SubApiClient

client = SubApiClient()
print(client.is_available("gemini"))
print(client.available_backends())
```

## CLI 사용

단발 질문:

```bash
sub_api ask "Python 데코레이터를 설명해줘." --model gemini
```

stdin에서 프롬프트 읽기:

```bash
echo "이 코드를 리뷰해줘" | sub_api ask --model claude
```

백엔드 상태 확인:

```bash
sub_api status
```

패키지 버전 확인:

```bash
sub_api version
```

## 서버 없이 직접 호출 테스트

서버를 띄우지 않고 실제 백엔드 CLI를 호출합니다.

```bash
python examples/direct_call.py "안녕" --model gemini
echo "간단히 요약해줘" | python examples/direct_call.py --model claude
```

CLI 인증이나 구독 상태와 무관하게 라이브러리 인터페이스만 빠르게 확인하려면 mock 기반 스모크 테스트를 실행합니다.

```bash
python examples/smoke_direct_client.py
```

## OpenAI 호환 서버

서버 의존성을 설치하고 서버를 실행합니다.

```bash
pip install "sub_api[server]"
sub_api serve --host 127.0.0.1 --port 8000
```

헬스체크:

```bash
curl http://127.0.0.1:8000/health
```

사용 가능한 모델 목록:

```bash
curl http://127.0.0.1:8000/v1/models
```

Chat Completions 호출:

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

## 외부 도구 설정

Cursor, Continue, Open WebUI, AnythingLLM 같은 도구에서는 다음 값을 사용합니다.

```text
Base URL: http://localhost:8000/v1
API Key: dummy
Model: gemini
```

## 오류 처리

Python 라이브러리 사용 시 다음 예외를 처리할 수 있습니다.

```python
from sub_api import (
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
    SubApiError,
)
```

서버 모드에서는 주로 다음 HTTP 상태 코드를 반환합니다.

- `400`: 지원하지 않는 모델 또는 옵션
- `503`: 백엔드 CLI가 설치되어 있지 않거나 `PATH`에서 찾을 수 없음
- `504`: 백엔드 CLI 타임아웃
- `500`: 백엔드 CLI 실행 실패 또는 출력 파싱 실패

## 환경 변수

`.env`에 다음 값을 둘 수 있습니다.

```env
HOST=127.0.0.1
PORT=8000
TIMEOUT=60
DEFAULT_BACKEND=gemini
```

## 현재 제한 사항

- 스트리밍 미지원
- tool/function calling 미지원
- 멀티모달 입력 미지원
- 토큰 사용량 계산 미지원
- `messages` 배열은 백엔드 CLI에 전달되기 전에 단일 프롬프트 문자열로 직렬화됨
