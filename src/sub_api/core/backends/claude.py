from __future__ import annotations

import os
import tempfile

from sub_api.core.backends.base import Backend


class ClaudeBackend(Backend):
    cli_name = "claude"

    def run_cli(self, prompt: str) -> str:
        with tempfile.TemporaryDirectory(prefix="sub-api-claude-") as temp_dir:
            env = os.environ.copy()
            env["CLAUDE_CONFIG_DIR"] = temp_dir
            return self._exec(self.cli_name, "-p", prompt, env=env)
