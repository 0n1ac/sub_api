from __future__ import annotations

from sub_api.core.backends.base import Backend
from sub_api.core.backends.claude import ClaudeBackend
from sub_api.core.backends.codex import CodexBackend
from sub_api.core.backends.gemini import GeminiBackend

BACKENDS: dict[str, type[Backend]] = {
    "gemini": GeminiBackend,
    "claude": ClaudeBackend,
    "codex": CodexBackend,
}


def get_backend(name: str, timeout: float) -> Backend:
    return BACKENDS[name](timeout=timeout)
