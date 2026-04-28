from __future__ import annotations

import json
from typing import Iterator

try:
    from fastapi import APIRouter
    from fastapi.responses import JSONResponse, StreamingResponse
    from starlette.concurrency import run_in_threadpool
except ImportError as exc:
    raise ImportError(
        "sub_api 서버 기능을 사용하려면 다음을 설치하세요:\n"
        "  pip install \"sub_api[server] @ git+https://github.com/0n1ac/sub_api.git\""
    ) from exc

from sub_api import SubApiClient
from sub_api.core.backends import BACKENDS
from sub_api.core.concurrency import BackendConcurrencyLimiter
from sub_api.core.config import get_settings
from sub_api.core.errors import (
    BackendConcurrencyTimeout,
    BackendExecutionError,
    BackendNotAvailable,
    BackendTimeout,
)
from sub_api.core.schema import ChatCompletionChunk, ChatCompletionRequest, ChatCompletionResponse


router = APIRouter(prefix="/v1", tags=["chat"])
settings = get_settings()
server_concurrency_limiter = BackendConcurrencyLimiter(
    settings.server_max_concurrent_per_backend
)


@router.get("/models")
async def models() -> dict[str, list[dict[str, str]]]:
    client = SubApiClient()
    available = set(client.available_backends())
    return {
        "object": "list",
        "data": [
            {"id": name, "object": "model", "owned_by": "sub_api"}
            for name in BACKENDS
            if name in available
        ],
    }


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse | JSONResponse | StreamingResponse:
    client = SubApiClient(
        timeout=request.timeout,
        concurrency_queue_timeout=(
            settings.concurrency_queue_timeout
            if settings.concurrency_queue_timeout is not None
            else request.timeout if request.timeout is not None
            else settings.timeout
        ),
        concurrency_limiter=server_concurrency_limiter,
    )
    messages = [message.model_dump() for message in request.messages]

    if request.stream:
        return StreamingResponse(
            _chat_completion_sse(client=client, request=request, messages=messages),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        return await run_in_threadpool(
            client.chat.completions.create,
            model=request.model,
            messages=messages,
            timeout=request.timeout,
        )
    except BackendNotAvailable as exc:
        return _error_response(503, str(exc))
    except BackendConcurrencyTimeout as exc:
        return _error_response(503, str(exc), error_type="backend_busy")
    except BackendTimeout as exc:
        return _error_response(504, str(exc))
    except BackendExecutionError as exc:
        status_code = 400 if _is_client_error(str(exc)) else 500
        return _error_response(status_code, str(exc))


def _error_response(
    status_code: int,
    message: str,
    error_type: str = "sub_api_error",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": None,
            }
        },
    )


def _is_client_error(message: str) -> bool:
    prefixes = (
        "Unsupported backend",
        "Model alias backend",
        "Streaming responses",
    )
    return message.startswith(prefixes)


def _chat_completion_sse(
    *,
    client: SubApiClient,
    request: ChatCompletionRequest,
    messages: list[dict[str, object]],
) -> Iterator[str]:
    try:
        chunks = client.chat.completions.create(
            model=request.model,
            messages=messages,
            stream=True,
            timeout=request.timeout,
        )
        assert not isinstance(chunks, ChatCompletionResponse)
        for chunk in chunks:
            yield _sse_data(chunk)
    except BackendConcurrencyTimeout as exc:
        yield _sse_error(str(exc), error_type="backend_busy")
    except BackendNotAvailable as exc:
        yield _sse_error(str(exc), error_type="backend_not_available")
    except BackendTimeout as exc:
        yield _sse_error(str(exc), error_type="backend_timeout")
    except BackendExecutionError as exc:
        yield _sse_error(str(exc))
    finally:
        yield "data: [DONE]\n\n"


def _sse_data(chunk: ChatCompletionChunk) -> str:
    payload = chunk.model_dump(mode="json", exclude_none=True)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_error(message: str, error_type: str = "sub_api_error") -> str:
    payload = {
        "error": {
            "message": message,
            "type": error_type,
            "param": None,
            "code": None,
        }
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
