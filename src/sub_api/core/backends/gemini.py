from __future__ import annotations

import json

from sub_api.core.backends.base import Backend, parse_jsonish_text


class GeminiBackend(Backend):
    cli_name = "gemini"

    def run_cli(self, prompt: str) -> str:
        return self._exec(
            self.cli_name,
            "-p",
            prompt,
            "--output-format",
            "json",
        )

    def parse_output(self, stdout: str) -> str:
        try:
            return parse_jsonish_text(stdout)
        except json.JSONDecodeError:
            return stdout
