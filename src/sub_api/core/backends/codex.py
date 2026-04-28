from __future__ import annotations

from typing import Iterator

from sub_api.core.backends.base import Backend, ExecResult, parse_stream_json_text


class CodexBackend(Backend):
    cli_name = "codex"

    def run_cli(self, prompt: str, model: str | None = None) -> ExecResult:
        return self._exec(
            self.cli_name,
            "exec",
            *self._model_args(model),
            "--ephemeral",
            prompt,
        )

    def run_cli_stream(self, prompt: str, model: str | None = None) -> Iterator[str]:
        yield from parse_stream_json_text(
            self._exec_stream(
                self.cli_name,
                "exec",
                *self._model_args(model),
                "--ephemeral",
                "--json",
                prompt,
            ),
            prompt_to_skip=prompt,
        )
