from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping

from sub_api.core.errors import BackendExecutionError, BackendNotAvailable, BackendTimeout
from sub_api.core.schema import ChatMessage


@dataclass(frozen=True)
class BackendResult:
    content: str


class Backend(ABC):
    cli_name: str

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def complete(self, messages: list[ChatMessage]) -> BackendResult:
        prompt = messages_to_prompt(messages)
        return self.call(prompt)

    def call(self, prompt: str) -> BackendResult:
        self.ensure_available()
        stdout = self.run_cli(prompt)
        content = self.parse_output(stdout).strip()
        if not content:
            raise BackendExecutionError(f"{self.cli_name} returned an empty response.")
        return BackendResult(content=content)

    def ensure_available(self) -> None:
        if shutil.which(self.cli_name) is None:
            raise BackendNotAvailable(
                f"'{self.cli_name}' CLI is not installed or not available on PATH."
            )

    def is_available(self) -> bool:
        return shutil.which(self.cli_name) is not None

    def version(self) -> str | None:
        if not self.is_available():
            return None
        for flag in ("--version", "-v"):
            try:
                output = self._exec(self.cli_name, flag, timeout=5)
            except BackendExecutionError:
                continue
            first_line = output.strip().splitlines()
            if first_line:
                return first_line[0]
        return None

    @abstractmethod
    def run_cli(self, prompt: str) -> str:
        raise NotImplementedError

    def parse_output(self, stdout: str) -> str:
        return stdout

    def _exec(
        self,
        *args: str,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> str:
        effective_timeout = self.timeout if timeout is None else timeout
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(env) if env is not None else None,
            text=True,
            start_new_session=True,
        )

        try:
            stdout, stderr = process.communicate(timeout=effective_timeout)
        except subprocess.TimeoutExpired as exc:
            _kill_process_group(process.pid)
            stdout, stderr = process.communicate()
            raise BackendTimeout(
                f"{self.cli_name} timed out after {effective_timeout:g} seconds."
            ) from exc

        if process.returncode != 0:
            message = stderr.strip() or stdout.strip() or f"exit code {process.returncode}"
            raise BackendExecutionError(f"{self.cli_name} failed: {message}")

        return stdout


def messages_to_prompt(messages: list[ChatMessage]) -> str:
    chunks: list[str] = []
    for message in messages:
        content = content_to_text(message.content)
        if content:
            chunks.append(f"{message.role}: {content}")
    return "\n\n".join(chunks)


def content_to_text(content: str | list[dict[str, object]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for part in content:
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            parts.append(part["text"])
    return "\n".join(parts)


def parse_jsonish_text(stdout: str) -> str:
    return extract_text(json.loads(stdout))


def extract_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (extract_text(item) for item in value)))
    if isinstance(value, dict):
        for key in ("text", "content", "response", "output"):
            if key in value:
                text = extract_text(value[key])
                if text:
                    return text
        for key in ("candidates", "parts"):
            if isinstance(value.get(key), list):
                return extract_text(value[key])
    return ""


def _kill_process_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
