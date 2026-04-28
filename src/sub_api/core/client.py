from __future__ import annotations

from typing import Any

from sub_api.core.backends import BACKENDS, get_backend
from sub_api.core.backends.base import BackendResult, messages_to_prompt
from sub_api.core.config import get_settings
from sub_api.core.errors import BackendExecutionError
from sub_api.core.modeling import ModelSelection, resolve_model_selection
from sub_api.core.schema import (
    ChatCompletionResponse,
    ChatMessage,
    make_chat_completion_response,
)


class SubApiClient:
    def __init__(self, default_backend: str | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self.default_backend = (default_backend or settings.default_backend).lower()
        self.timeout = settings.timeout if timeout is None else timeout
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
        result = backend_impl.call(prompt, model=selection.model)
        self.last_result = result
        return result

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
    ) -> ChatCompletionResponse:
        if stream:
            raise BackendExecutionError("Streaming responses are not supported by this prototype.")

        parsed_messages = [
            message if isinstance(message, ChatMessage) else ChatMessage.model_validate(message)
            for message in messages
        ]
        selection = self._client._resolve_selection(model=model)
        prompt = messages_to_prompt(parsed_messages)
        result = self._client.call_result(
            prompt=prompt,
            backend=selection.backend,
            model=selection.model,
            timeout=timeout,
        )
        return make_chat_completion_response(
            model=selection.response_model,
            content=result.content,
            sub_api={
                "backend": selection.backend,
                "latency_ms": result.latency.as_dict(),
            },
        )
