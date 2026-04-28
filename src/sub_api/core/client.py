from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any, Iterator

from sub_api.core.backends import BACKENDS, get_backend
from sub_api.core.backends.base import (
    BackendResult,
    LatencyStats,
    estimate_usage,
    messages_to_prompt,
)
from sub_api.core.config import get_settings
from sub_api.core.concurrency import BackendConcurrencyLimiter
from sub_api.core.errors import BackendExecutionError
from sub_api.core.modeling import ModelSelection, resolve_model_selection
from sub_api.core.schema import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    make_chat_completion_chunk,
    make_chat_completion_response,
)


@dataclass
class StreamingResult:
    chunks: Iterator[str]
    result: BackendResult | None = None


class SubApiClient:
    def __init__(
        self,
        default_backend: str | None = None,
        timeout: float | None = None,
        max_concurrent_per_backend: int | None = 1,
        concurrency_queue_timeout: float | None = None,
        concurrency_limiter: BackendConcurrencyLimiter | None = None,
    ) -> None:
        settings = get_settings()
        self.default_backend = (default_backend or settings.default_backend).lower()
        self.timeout = settings.timeout if timeout is None else timeout
        self.concurrency_queue_timeout = (
            settings.concurrency_queue_timeout
            if concurrency_queue_timeout is None
            else concurrency_queue_timeout
        )
        self._concurrency_limiter = concurrency_limiter
        if self._concurrency_limiter is None and max_concurrent_per_backend is not None:
            self._concurrency_limiter = BackendConcurrencyLimiter(max_concurrent_per_backend)
        self.last_result: BackendResult | None = None
        self.chat = _ChatResource(self)

    def call(
        self,
        prompt: str,
        *,
        backend: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> str:
        return self.call_result(
            prompt=prompt,
            backend=backend,
            model=model,
            timeout=timeout,
        ).content

    def call_result(
        self,
        prompt: str,
        *,
        backend: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> BackendResult:
        selection = self._resolve_selection(backend=backend, model=model)
        backend_impl = get_backend(
            selection.backend,
            timeout=self.timeout if timeout is None else timeout,
        )
        if self._concurrency_limiter is None:
            result = backend_impl.call(prompt, model=selection.model)
            self.last_result = result
            return result

        total_start = time.perf_counter()
        queue_timeout = (
            self.concurrency_queue_timeout
            if self.concurrency_queue_timeout is not None
            else timeout if timeout is not None
            else self.timeout
        )
        with self._concurrency_limiter.acquire(selection.backend, timeout=queue_timeout) as slot:
            result = backend_impl.call(prompt, model=selection.model)
        result = _with_concurrency_latency(result, queued_ms=slot.queued_ms, total_start=total_start)
        self.last_result = result
        return result

    def stream(
        self,
        prompt: str,
        *,
        backend: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> Iterator[str]:
        yield from self.stream_result(
            prompt=prompt,
            backend=backend,
            model=model,
            timeout=timeout,
        ).chunks

    def stream_result(
        self,
        prompt: str,
        *,
        backend: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> StreamingResult:
        selection = self._resolve_selection(backend=backend, model=model)
        backend_impl = get_backend(
            selection.backend,
            timeout=self.timeout if timeout is None else timeout,
        )

        stream_result = StreamingResult(chunks=iter(()))

        def chunks() -> Iterator[str]:
            total_start = time.perf_counter()
            stream_start: float | None = None
            first_chunk_at: float | None = None
            queued_ms: int | None = None
            backend_latency: LatencyStats | None = None
            parts: list[str] = []
            tools: list[str] = []

            if self._concurrency_limiter is None:
                stream_start = time.perf_counter()
                for event in backend_impl.stream_events(prompt, model=selection.model):
                    if event.latency is not None:
                        backend_latency = event.latency
                        continue
                    if event.tool_name:
                        tools.append(event.tool_name)
                        continue
                    if event.text is None:
                        continue
                    chunk = event.text
                    if first_chunk_at is None:
                        first_chunk_at = time.perf_counter()
                    parts.append(chunk)
                    yield chunk
            else:
                queue_timeout = (
                    self.concurrency_queue_timeout
                    if self.concurrency_queue_timeout is not None
                    else timeout if timeout is not None
                    else self.timeout
                )
                with self._concurrency_limiter.acquire(
                    selection.backend,
                    timeout=queue_timeout,
                ) as slot:
                    queued_ms = slot.queued_ms
                    stream_start = time.perf_counter()
                    for event in backend_impl.stream_events(prompt, model=selection.model):
                        if event.latency is not None:
                            backend_latency = event.latency
                            continue
                        if event.tool_name:
                            tools.append(event.tool_name)
                            continue
                        if event.text is None:
                            continue
                        chunk = event.text
                        if first_chunk_at is None:
                            first_chunk_at = time.perf_counter()
                        parts.append(chunk)
                        yield chunk

            finished_at = time.perf_counter()
            content = "".join(parts)
            result = BackendResult(
                content=content,
                latency=LatencyStats(
                    total=_elapsed_ms(total_start),
                    queued=queued_ms,
                    spawn=backend_latency.spawn if backend_latency else None,
                    first_stdout=(
                        backend_latency.first_stdout
                        if backend_latency and backend_latency.first_stdout is not None
                        else _interval_ms(total_start, first_chunk_at)
                    ),
                    first_content=_interval_ms(total_start, first_chunk_at),
                    execution=(
                        backend_latency.execution
                        if backend_latency and backend_latency.execution is not None
                        else _interval_ms(stream_start, finished_at)
                    ),
                    parse=0,
                ),
                usage=estimate_usage(prompt=prompt, completion=content, model=selection.model),
                tools=tuple(_dedupe_preserving_order(tools)),
            )
            stream_result.result = result
            self.last_result = result

        stream_result.chunks = chunks()
        return stream_result

    def is_available(self, backend: str) -> bool:
        selection = self._resolve_selection(backend=backend)
        return get_backend(selection.backend, timeout=5).is_available()

    def available_backends(self) -> list[str]:
        return [name for name in BACKENDS if self.is_available(name)]

    def backend_versions(self) -> dict[str, str | None]:
        versions: dict[str, str | None] = {}
        for name in BACKENDS:
            backend = get_backend(name, timeout=5)
            versions[name] = backend.version()
        return versions

    def _resolve_selection(
        self,
        *,
        backend: str | None = None,
        model: str | None = None,
    ) -> ModelSelection:
        return resolve_model_selection(
            available_backends=set(BACKENDS),
            default_backend=self.default_backend,
            backend=backend,
            model=model,
        )


class _ChatResource:
    def __init__(self, client: SubApiClient) -> None:
        self.completions = _CompletionsResource(client)


class _CompletionsResource:
    def __init__(self, client: SubApiClient) -> None:
        self._client = client

    def create(
        self,
        *,
        model: str | None = None,
        messages: list[dict[str, Any] | ChatMessage],
        stream: bool = False,
        timeout: float | None = None,
        **_: Any,
    ) -> ChatCompletionResponse | Iterator[ChatCompletionChunk]:
        parsed_messages = [
            message if isinstance(message, ChatMessage) else ChatMessage.model_validate(message)
            for message in messages
        ]
        selection = self._client._resolve_selection(model=model)
        prompt = messages_to_prompt(parsed_messages)

        if stream:
            stream_result = self._client.stream_result(
                prompt=prompt,
                backend=selection.backend,
                model=selection.model,
                timeout=timeout,
            )
            return _chat_completion_chunks(
                stream_result,
                model=selection.response_model,
                backend=selection.backend,
            )

        result = self._client.call_result(
            prompt=prompt,
            backend=selection.backend,
            model=selection.model,
            timeout=timeout,
        )
        return make_chat_completion_response(
            model=selection.response_model,
            content=result.content,
            usage=result.usage.as_openai_usage(),
            sub_api={
                "backend": selection.backend,
                "latency_ms": result.latency.as_dict(),
                "tools": list(result.tools),
                "usage": {
                    "source": result.usage.source,
                },
            },
        )


def _with_concurrency_latency(
    result: BackendResult,
    *,
    queued_ms: int,
    total_start: float,
) -> BackendResult:
    latency = result.latency
    updated_latency = LatencyStats(
        total=int(round((time.perf_counter() - total_start) * 1000)),
        queued=queued_ms,
        spawn=latency.spawn,
        first_stdout=latency.first_stdout,
        execution=latency.execution,
        parse=latency.parse,
    )
    return replace(result, latency=updated_latency)


def _chat_completion_chunks(
    stream_result: StreamingResult,
    *,
    model: str,
    backend: str,
) -> Iterator[ChatCompletionChunk]:
    chunk_id = f"sub_api-chatcmpl-{int(time.time() * 1000)}"
    created = int(time.time())
    yield make_chat_completion_chunk(
        chunk_id=chunk_id,
        created=created,
        model=model,
        role="assistant",
        sub_api={"backend": backend},
    )
    for content in stream_result.chunks:
        if content:
            yield make_chat_completion_chunk(
                chunk_id=chunk_id,
                created=created,
                model=model,
                content=content,
            )
    result = stream_result.result
    sub_api = None
    usage = None
    if result is not None:
        usage = result.usage.as_openai_usage()
        sub_api = {
            "backend": backend,
            "latency_ms": result.latency.as_dict(),
            "tools": list(result.tools),
            "usage": {
                "source": result.usage.source,
            },
        }
    yield make_chat_completion_chunk(
        chunk_id=chunk_id,
        created=created,
        model=model,
        finish_reason="stop",
        usage=usage,
        sub_api=sub_api,
    )


def _elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


def _interval_ms(start: float | None, end: float | None) -> int | None:
    if start is None or end is None:
        return None
    return int(round((end - start) * 1000))


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
