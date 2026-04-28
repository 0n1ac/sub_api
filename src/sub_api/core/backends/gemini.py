from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterator

from sub_api.core.backends.base import (
    Backend,
    ExecResult,
    StreamChunk,
    parse_jsonish_text,
    parse_stream_json_text,
)


_DISABLE_TOOLS_SETTINGS = {
    "admin": {
        "extensions": {"enabled": False},
        "mcp": {"enabled": False},
        "skills": {"enabled": False},
    },
    "skills": {
        "enabled": False,
    },
    "tools": {
        "core": ["save_memory"],
    }
}


class GeminiBackend(Backend):
    cli_name = "gemini"

    def run_cli(self, prompt: str, model: str | None = None) -> ExecResult:
        env = os.environ.copy()
        env.setdefault("GEMINI_CLI_TRUST_WORKSPACE", "true")
        _apply_tool_env(env)

        return self._exec(
            self.cli_name,
            *self._model_args(model),
            "-p",
            prompt,
            "--output-format",
            "json",
            env=env,
        )

    def parse_output(self, stdout: str) -> str:
        try:
            return parse_jsonish_text(stdout)
        except json.JSONDecodeError:
            return stdout

    def run_cli_stream(self, prompt: str, model: str | None = None) -> Iterator[StreamChunk]:
        env = os.environ.copy()
        env.setdefault("GEMINI_CLI_TRUST_WORKSPACE", "true")
        _apply_tool_env(env)

        yield from parse_stream_json_text(
            self._exec_stream(
                self.cli_name,
                *self._model_args(model),
                "-p",
                prompt,
                "--output-format",
                "stream-json",
                env=env,
            ),
            prompt_to_skip=prompt,
        )

    def _tool_args(self) -> list[str]:
        return []


def _apply_tool_env(env: dict[str, str]) -> None:
    if not _disable_tools_enabled(env):
        return
    env["GEMINI_CLI_SYSTEM_SETTINGS_PATH"] = str(_disable_tools_settings_path())


def _disable_tools_enabled(env: dict[str, str]) -> bool:
    return env.get("SUB_API_GEMINI_DISABLE_TOOLS", "").lower() in {"1", "true", "yes", "on"}


def _disable_tools_settings_path() -> Path:
    settings_path = Path(tempfile.gettempdir()) / "sub_api" / "gemini-disable-tools-settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(_DISABLE_TOOLS_SETTINGS, indent=2) + "\n"
    if not settings_path.exists() or settings_path.read_text(encoding="utf-8") != content:
        settings_path.write_text(content, encoding="utf-8")
    return settings_path
