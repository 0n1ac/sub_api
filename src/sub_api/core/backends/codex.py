from __future__ import annotations

from sub_api.core.backends.base import Backend


class CodexBackend(Backend):
    cli_name = "codex"

    def run_cli(self, prompt: str, model: str | None = None) -> str:
        return self._exec(
            self.cli_name,
            "exec",
            *self._model_args(model),
            "--ephemeral",
            prompt,
        )
