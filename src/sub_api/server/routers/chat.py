from __future__ import annotations

try:
    from fastapi import APIRouter
    from fastapi.responses import JSONResponse
    from starlette.concurrency import run_in_threadpool
except ImportError as exc:
    raise ImportError(
        "sub_api 서버 기능을 사용하려면 다음을 설치하세요:\n"
        "  pip install \"sub_api[server] @ git+https://github.com/0n1ac/sub_api.git\""
    ) from exc

from sub_api import SubApiClient
from sub_api.core.backends import BACKENDS
from sub_api.core.errors import BackendExecutionError, BackendNotAvailable, BackendTimeout
from sub_api.core.schema import ChatCompletionRequest, ChatCompletionResponse


router = APIRouter(prefix="/v1", tags=["chat"])


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
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse | JSONResponse:
    if request.stream:
        return _error_response(
            400,
            "Streaming responses are not supported by this prototype.",
        )

    client = SubApiClient(timeout=request.timeout)
    messages = [message.model_dump() for message in request.messages]

    try:
        return await run_in_threadpool(
            client.chat.completions.create,
            model=request.model,
            messages=messages,
            timeout=request.timeout,
        )
    except BackendNotAvailable as exc:
        return _error_response(503, str(exc))
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
