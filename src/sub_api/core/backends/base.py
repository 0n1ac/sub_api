from __future__ import annotations

import json
import math
import os
import selectors
import shutil
import signal
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Mapping

from sub_api.core.errors import BackendExecutionError, BackendNotAvailable, BackendTimeout
from sub_api.core.schema import ChatMessage


@dataclass(frozen=True)
class LatencyStats:
    total: int | None = None
    queued: int | None = None
    spawn: int | None = None
    first_stdout: int | None = None
    execution: int | None = None
    parse: int | None = None

    def as_dict(self) -> dict[str, int | None]:
        return {
            "total": self.total,
            "queued": self.queued,
            "spawn": self.spawn,
            "first_stdout": self.first_stdout,
            "execution": self.execution,
            "parse": self.parse,
        }


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    latency: LatencyStats


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    source: str

    def as_openai_usage(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class BackendResult:
    content: str
    latency: LatencyStats
    usage: TokenUsage


class Backend(ABC):
    cli_name: str
    model_flag: tuple[str, ...] = ("--model",)
    supports_stdout_streaming: bool = True

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def complete(self, messages: list[ChatMessage], model: str | None = None) -> BackendResult:
        prompt = messages_to_prompt(messages)
        return self.call(prompt, model=model)

    def call(self, prompt: str, model: str | None = None) -> BackendResult:
        total_start = time.perf_counter()
        self.ensure_available()
        exec_result = self.run_cli(prompt, model=model)

        parse_start = time.perf_counter()
        content = self.parse_output(exec_result.stdout).strip()
        parse_ms = _elapsed_ms(parse_start)

        if not content:
            raise BackendExecutionError(f"{self.cli_name} returned an empty response.")

        usage = extract_native_usage(exec_result.stdout)
        if usage is None:
            usage = estimate_usage(prompt=prompt, completion=content, model=model)

        latency = LatencyStats(
            total=_elapsed_ms(total_start),
            spawn=exec_result.latency.spawn,
            first_stdout=exec_result.latency.first_stdout,
            execution=exec_result.latency.execution,
            parse=parse_ms,
        )
        return BackendResult(content=content, latency=latency, usage=usage)

    def stream(self, prompt: str, model: str | None = None) -> Iterator[str]:
        if not self.supports_stdout_streaming:
            yield self.call(prompt, model=model).content
            return

        self.ensure_available()
        yield from self.run_cli_stream(prompt, model=model)

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
                output = self._exec(self.cli_name, flag, timeout=5).stdout
            except BackendExecutionError:
                continue
            first_line = output.strip().splitlines()
            if first_line:
                return first_line[0]
        return None

    @abstractmethod
    def run_cli(self, prompt: str, model: str | None = None) -> ExecResult:
        raise NotImplementedError

    def run_cli_stream(self, prompt: str, model: str | None = None) -> Iterator[str]:
        raise BackendExecutionError(f"{self.cli_name} does not support stdout streaming.")

    def parse_output(self, stdout: str) -> str:
        return stdout

    def _exec(
        self,
        *args: str,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> ExecResult:
        effective_timeout = self.timeout if timeout is None else timeout
        total_start = time.perf_counter()
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(env) if env is not None else None,
            start_new_session=True,
        )
        process_started_at = time.perf_counter()
        spawn_ms = _interval_ms(total_start, process_started_at)

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        first_stdout_at: float | None = None
        last_stdout_at: float | None = None

        timed_out = False
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, stdout_chunks)
        selector.register(process.stderr, selectors.EVENT_READ, stderr_chunks)

        deadline = total_start + effective_timeout

        try:
            while selector.get_map():
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    timed_out = True
                    break

                events = selector.select(timeout=min(0.1, remaining))
                if not events and process.poll() is not None:
                    _drain_ready_streams(selector)
                    break

                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue

                    key.data.append(chunk)
                    if key.data is stdout_chunks:
                        now = time.perf_counter()
                        if first_stdout_at is None:
                            first_stdout_at = now
                        last_stdout_at = now

            if timed_out:
                _kill_process_group(process.pid)
                _drain_process_pipes(process, stdout_chunks, stderr_chunks)
                raise BackendTimeout(
                    f"{self.cli_name} timed out after {effective_timeout:g} seconds."
                )

            try:
                return_code = process.wait(timeout=1)
                process_finished_at = time.perf_counter()
            except subprocess.TimeoutExpired as exc:
                _kill_process_group(process.pid)
                _drain_process_pipes(process, stdout_chunks, stderr_chunks)
                raise BackendTimeout(
                    f"{self.cli_name} timed out after {effective_timeout:g} seconds."
                ) from exc
        finally:
            selector.close()

        stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")

        if return_code != 0:
            message = stderr.strip() or stdout.strip() or f"exit code {return_code}"
            raise BackendExecutionError(f"{self.cli_name} failed: {message}")

        return ExecResult(
            stdout=stdout,
            latency=LatencyStats(
                spawn=spawn_ms,
                first_stdout=_interval_ms(total_start, first_stdout_at),
                execution=_interval_ms(process_started_at, process_finished_at),
            ),
        )

    def _exec_stream(
        self,
        *args: str,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Iterator[str]:
        effective_timeout = self.timeout if timeout is None else timeout
        total_start = time.perf_counter()
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(env) if env is not None else None,
            start_new_session=True,
        )

        stderr_chunks: list[bytes] = []
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        assert process.stderr is not None
        selector.register(process.stdout, selectors.EVENT_READ, None)
        selector.register(process.stderr, selectors.EVENT_READ, stderr_chunks)
        deadline = total_start + effective_timeout
        timed_out = False

        try:
            while selector.get_map():
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    timed_out = True
                    break

                events = selector.select(timeout=min(0.1, remaining))
                if not events and process.poll() is not None:
                    break

                for key, _ in events:
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue

                    if key.fileobj is process.stdout:
                        yield chunk.decode("utf-8", errors="replace")
                    else:
                        key.data.append(chunk)

            if timed_out:
                _kill_process_group(process.pid)
                _drain_process_pipes(process, [], stderr_chunks)
                raise BackendTimeout(
                    f"{self.cli_name} timed out after {effective_timeout:g} seconds."
                )

            try:
                return_code = process.wait(timeout=1)
            except subprocess.TimeoutExpired as exc:
                _kill_process_group(process.pid)
                _drain_process_pipes(process, [], stderr_chunks)
                raise BackendTimeout(
                    f"{self.cli_name} timed out after {effective_timeout:g} seconds."
                ) from exc
        finally:
            selector.close()
            if process.poll() is None:
                _kill_process_group(process.pid)

        remaining_stdout = process.stdout.read()
        if remaining_stdout:
            yield remaining_stdout.decode("utf-8", errors="replace")
        remaining_stderr = process.stderr.read()
        if remaining_stderr:
            stderr_chunks.append(remaining_stderr)

        stderr = b"".join(stderr_chunks).decode("utf-8", errors="replace")
        if return_code != 0:
            message = stderr.strip() or f"exit code {return_code}"
            raise BackendExecutionError(f"{self.cli_name} failed: {message}")

    def _model_args(self, model: str | None) -> list[str]:
        if model is None:
            return []
        args: list[str] = []
        for flag in self.model_flag:
            args.append(flag)
        args.append(model)
        return args


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


def parse_stream_json_text(chunks: Iterator[str]) -> Iterator[str]:
    buffer = ""
    emitted_text = ""
    for chunk in chunks:
        buffer += chunk
        lines = buffer.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            buffer = lines.pop()
        else:
            buffer = ""

        for line in lines:
            text = _stream_json_line_text(line.strip())
            if text:
                delta = _dedupe_stream_text(emitted_text, text)
                if delta:
                    emitted_text += delta
                    yield delta

    if buffer:
        text = _stream_json_line_text(buffer.strip())
        if text:
            delta = _dedupe_stream_text(emitted_text, text)
            if delta:
                yield delta


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


def _stream_json_line_text(line: str) -> str:
    if not line:
        return ""

    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return line

    text = _extract_stream_delta_text(event)
    if text:
        return text

    event_type = event.get("type") if isinstance(event, dict) else None
    if event_type in {"result", "final", "message"}:
        return extract_text(event)
    return ""


def _dedupe_stream_text(emitted_text: str, text: str) -> str:
    if not emitted_text:
        return text
    if text.startswith(emitted_text):
        return text[len(emitted_text) :]
    return text


def _extract_stream_delta_text(value: object) -> str:
    if isinstance(value, str):
        return ""

    if isinstance(value, list):
        return "".join(_extract_stream_delta_text(item) for item in value)

    if not isinstance(value, dict):
        return ""

    for key in ("delta", "partial", "chunk"):
        nested = value.get(key)
        if isinstance(nested, str):
            return nested
        text = _extract_stream_text_leaf(nested)
        if text:
            return text

    if value.get("type") in {
        "content_block_delta",
        "message_delta",
        "response.output_text.delta",
        "thread.message.delta",
        "assistant_delta",
    }:
        text = _extract_stream_text_leaf(value)
        if text:
            return text

    for nested in value.values():
        text = _extract_stream_delta_text(nested)
        if text:
            return text

    return ""


def _extract_stream_text_leaf(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_extract_stream_text_leaf(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "content", "output_text"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
        for nested in value.values():
            text = _extract_stream_text_leaf(nested)
            if text:
                return text
    return ""


def extract_native_usage(stdout: str) -> TokenUsage | None:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None

    usage_dict = _find_usage_dict(data)
    if usage_dict is None:
        return None

    prompt_tokens = _first_int(
        usage_dict,
        (
            "prompt_tokens",
            "input_tokens",
            "promptTokenCount",
            "inputTokens",
            "inputTokenCount",
        ),
    )
    completion_tokens = _first_int(
        usage_dict,
        (
            "completion_tokens",
            "output_tokens",
            "candidatesTokenCount",
            "outputTokens",
            "outputTokenCount",
        ),
    )
    total_tokens = _first_int(
        usage_dict,
        (
            "total_tokens",
            "totalTokenCount",
            "totalTokens",
        ),
    )

    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

    if total_tokens is None:
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
    if prompt_tokens is None:
        prompt_tokens = max(total_tokens - (completion_tokens or 0), 0)
    if completion_tokens is None:
        completion_tokens = max(total_tokens - prompt_tokens, 0)

    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        source="native",
    )


def estimate_usage(prompt: str, completion: str, model: str | None = None) -> TokenUsage:
    tiktoken_counts = _estimate_with_tiktoken(prompt, completion, model=model)
    if tiktoken_counts is not None:
        prompt_tokens, completion_tokens = tiktoken_counts
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            source="tiktoken_estimate",
        )

    prompt_tokens = _heuristic_token_count(prompt)
    completion_tokens = _heuristic_token_count(completion)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        source="heuristic",
    )


def _find_usage_dict(value: object) -> dict[str, object] | None:
    if isinstance(value, dict):
        for key in ("usage", "usageMetadata", "usage_metadata", "tokenUsage"):
            nested = value.get(key)
            if isinstance(nested, dict):
                return nested

        if _looks_like_usage_dict(value):
            return value

        for nested in value.values():
            found = _find_usage_dict(nested)
            if found is not None:
                return found

    if isinstance(value, list):
        for item in value:
            found = _find_usage_dict(item)
            if found is not None:
                return found

    return None


def _looks_like_usage_dict(value: dict[str, object]) -> bool:
    token_keys = {
        "prompt_tokens",
        "input_tokens",
        "promptTokenCount",
        "inputTokens",
        "inputTokenCount",
        "completion_tokens",
        "output_tokens",
        "candidatesTokenCount",
        "outputTokens",
        "outputTokenCount",
        "total_tokens",
        "totalTokenCount",
        "totalTokens",
    }
    return any(key in value for key in token_keys)


def _first_int(value: dict[str, object], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        raw = value.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(raw)
        if isinstance(raw, str) and raw.isdigit():
            return int(raw)
    return None


def _estimate_with_tiktoken(
    prompt: str,
    completion: str,
    model: str | None,
) -> tuple[int, int] | None:
    try:
        import tiktoken  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        encoding = tiktoken.encoding_for_model(model) if model else tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(prompt)), len(encoding.encode(completion))


def _heuristic_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _kill_process_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def _elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


def _interval_ms(start: float | None, end: float | None) -> int | None:
    if start is None or end is None:
        return None
    return int(round((end - start) * 1000))


def _drain_ready_streams(selector: selectors.BaseSelector) -> None:
    for key in list(selector.get_map().values()):
        while True:
            try:
                chunk = os.read(key.fileobj.fileno(), 8192)
            except BlockingIOError:
                break
            if not chunk:
                try:
                    selector.unregister(key.fileobj)
                except KeyError:
                    pass
                break
            key.data.append(chunk)


def _drain_process_pipes(
    process: subprocess.Popen[bytes],
    stdout_chunks: list[bytes],
    stderr_chunks: list[bytes],
) -> None:
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    if stdout:
        stdout_chunks.append(stdout)
    if stderr:
        stderr_chunks.append(stderr)
