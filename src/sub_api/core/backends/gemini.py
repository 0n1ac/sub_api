from __future__ import annotations

import json
import os

from typing import Iterator

from sub_api.core.backends.base import (
    Backend,
    ExecResult,
    parse_jsonish_text,
    parse_stream_json_text,
)


class GeminiBackend(Backend):
    cli_name = "gemini"

    def run_cli(self, prompt: str, model: str | None = None) -> ExecResult:
        env = os.environ.copy()
        env.setdefault("GEMINI_CLI_TRUST_WORKSPACE", "true")

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

    def run_cli_stream(self, prompt: str, model: str | None = None) -> Iterator[str]:
        env = os.environ.copy()
        env.setdefault("GEMINI_CLI_TRUST_WORKSPACE", "true")

        yield from parse_stream_json_text(
            self._exec_stream(
                self.cli_name,
                *self._model_args(model),
                "-p",
                prompt,
                "--output-format",
                "stream-json",
                env=env,
            )
        )
