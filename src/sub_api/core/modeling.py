from __future__ import annotations

import os
from dataclasses import dataclass

from sub_api.core.errors import BackendExecutionError


@dataclass(frozen=True)
class ModelSelection:
    backend: str
    model: str | None

    @property
    def response_model(self) -> str:
        if self.model:
            return f"{self.backend}/{self.model}"
        return self.backend


def resolve_model_selection(
    *,
    available_backends: set[str],
    default_backend: str,
    backend: str | None = None,
    model: str | None = None,
) -> ModelSelection:
    requested_backend = _normalize_backend(backend) if backend else None
    requested_model = _strip_provider_prefix(model)

    if requested_model and "/" in requested_model:
        alias_backend, alias_model = requested_model.split("/", 1)
        alias_backend = _normalize_backend(alias_backend)
        alias_model = alias_model.strip() or None

        if requested_backend and requested_backend != alias_backend:
            raise BackendExecutionError(
                f"Model alias backend '{alias_backend}' does not match backend '{requested_backend}'."
            )

        requested_backend = alias_backend
        requested_model = alias_model

    if requested_backend is None:
        if requested_model and _normalize_backend(requested_model) in available_backends:
            requested_backend = _normalize_backend(requested_model)
            requested_model = None
        else:
            requested_backend = _normalize_backend(default_backend)

    if requested_backend not in available_backends:
        supported = ", ".join(sorted(available_backends))
        raise BackendExecutionError(
            f"Unsupported backend '{requested_backend}'. Supported backends: {supported}."
        )

    if requested_model is None:
        requested_model = _default_model_for_backend(requested_backend)

    return ModelSelection(backend=requested_backend, model=requested_model)


def _normalize_backend(value: str) -> str:
    return value.strip().lower()


def _strip_provider_prefix(model: str | None) -> str | None:
    if model is None:
        return None

    normalized = model.strip()
    if normalized.startswith("openai/"):
        return normalized.split("/", 1)[1]
    return normalized


def _default_model_for_backend(backend: str) -> str | None:
    value = os.getenv(f"SUB_API_DEFAULT_MODEL_{backend.upper()}")
    if value is None or not value.strip():
        return None
    return value.strip()
