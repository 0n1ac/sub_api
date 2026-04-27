from __future__ import annotations

try:
    from fastapi import FastAPI
except ImportError as exc:
    raise ImportError(
        "sub_api 서버 기능을 사용하려면 다음을 설치하세요:\n"
        "  pip install sub_api[server]"
    ) from exc

from sub_api.server.routers.chat import router as chat_router


app = FastAPI(
    title="sub_api",
    version="0.2.0",
    description="OpenAI-compatible adapter for the sub_api core library.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chat_router)
