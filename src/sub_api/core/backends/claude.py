from __future__ import annotations

import os
import tempfile
from typing import Iterator

from sub_api.core.backends.base import Backend, ExecResult, parse_stream_json_text


class ClaudeBackend(Backend):
    cli_name = "claude"

    def run_cli(self, prompt: str, model: str | None = None) -> ExecResult:
        with tempfile.TemporaryDirectory(prefix="sub-api-claude-") as temp_dir:
            env = os.environ.copy()
            env["CLAUDE_CONFIG_DIR"] = temp_dir
            return self._exec(
                self.cli_name,
                *self._model_args(model),
                "-p",
                prompt,
                env=env,
            )

    def run_cli_stream(self, prompt: str, model: str | None = None) -> Iterator[str]:
        with tempfile.TemporaryDirectory(prefix="sub-api-claude-") as temp_dir:
            env = os.environ.copy()
            env["CLAUDE_CONFIG_DIR"] = temp_dir
            yield from parse_stream_json_text(
                self._exec_stream(
                    self.cli_name,
                    *self._model_args(model),
                    "-p",
                    prompt,
                    "--output-format",
                    "stream-json",
                    "--include-partial-messages",
                    env=env,
                )
            )
