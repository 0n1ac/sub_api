from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    timeout: float | None = None


class CompletionMessage(BaseModel):
    role: str = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    index: int
    message: CompletionMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, Any] | None = None
    sub_api: dict[str, Any] | None = None


class CompletionDelta(BaseModel):
    role: str | None = None
    content: str | None = None


class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: CompletionDelta
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatCompletionChunkChoice]
    sub_api: dict[str, Any] | None = None


def make_chat_completion_response(
    model: str,
    content: str,
    usage: dict[str, Any] | None = None,
    sub_api: dict[str, Any] | None = None,
) -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id=f"sub_api-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=CompletionMessage(content=content),
            )
        ],
        usage=usage,
        sub_api=sub_api,
    )


def make_chat_completion_chunk(
    *,
    chunk_id: str,
    created: int,
    model: str,
    content: str | None = None,
    role: str | None = None,
    finish_reason: str | None = None,
    sub_api: dict[str, Any] | None = None,
) -> ChatCompletionChunk:
    return ChatCompletionChunk(
        id=chunk_id,
        created=created,
        model=model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=CompletionDelta(role=role, content=content),
                finish_reason=finish_reason,
            )
        ],
        sub_api=sub_api,
    )
