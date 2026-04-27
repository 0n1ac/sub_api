from __future__ import annotations

from typing import Any

from sub_api.core.backends import BACKENDS, get_backend
from sub_api.core.backends.base import messages_to_prompt
from sub_api.core.config import get_settings
from sub_api.core.errors import BackendExecutionError
from sub_api.core.schema import (
    ChatCompletionResponse,
    ChatMessage,
    make_chat_completion_response,
)


class SubApiClient:
    def __init__(self, default_model: str | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self.default_model = (default_model or settings.default_backend).lower()
        self.timeout = settings.timeout if timeout is None else timeout
        self.chat = _ChatResource(self)

    def call(
        self,
        model: str | None = None,
        prompt: str | None = None,
        timeout: float | None = None,
    ) -> str:
        if prompt is None:
            prompt = model
            model = None
        if prompt is None:
            raise BackendExecutionError("Prompt is required.")

        model_name = self._normalize_model(model)
        backend = get_backend(model_name, timeout=self.timeout if timeout is None else timeout)
        return backend.call(prompt).content

    def is_available(self, model: str) -> bool:
        model_name = self._normalize_model(model)
        return get_backend(model_name, timeout=5).is_available()

    def available_backends(self) -> list[str]:
        return [name for name in BACKENDS if self.is_available(name)]

    def backend_versions(self) -> dict[str, str | None]:
        versions: dict[str, str | None] = {}
        for name in BACKENDS:
            backend = get_backend(name, timeout=5)
            versions[name] = backend.version()
        return versions

    def _normalize_model(self, model: str | None) -> str:
        model_name = (model or self.default_model).lower()
        if model_name.startswith("openai/"):
            model_name = model_name.split("/", 1)[1]
        if model_name not in BACKENDS:
            supported = ", ".join(BACKENDS)
            raise BackendExecutionError(
                f"Unsupported model '{model_name}'. Supported models: {supported}."
            )
        return model_name


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
        model_name = self._client._normalize_model(model)
        prompt = messages_to_prompt(parsed_messages)
        content = self._client.call(model=model_name, prompt=prompt, timeout=timeout)
        return make_chat_completion_response(model=model_name, content=content)
