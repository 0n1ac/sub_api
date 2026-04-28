from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from sub_api import SubApiClient
from sub_api.core.backends.base import BackendResult, LatencyStats, StreamChunk, TokenUsage


class FakeBackend:
    # This fake backend mirrors the minimal interface used by SubApiClient.
    # It lets the example run without installing or authenticating any real CLI.
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def call(self, prompt: str, model: str | None = None) -> BackendResult:
        if prompt.startswith("slow"):
            time.sleep(0.05)

        # Real backends return BackendResult(content=...) after subprocess output
        # has been parsed. The fake response keeps assertions deterministic.
        model_label = model or "default"
        return BackendResult(
            content=f"fake response ({model_label}): {prompt}",
            latency=LatencyStats(total=12, spawn=1, first_stdout=2, execution=10, parse=1),
            usage=TokenUsage(
                prompt_tokens=2,
                completion_tokens=3,
                total_tokens=5,
                source="heuristic",
            ),
        )

    def stream(self, prompt: str, model: str | None = None):
        for event in self.stream_events(prompt, model=model):
            if event.text:
                yield event.text

    def stream_events(self, prompt: str, model: str | None = None):
        yield StreamChunk(text="fake ")
        yield StreamChunk(text=f"stream ({model or 'default'}): {prompt}")
        yield StreamChunk(
            latency=LatencyStats(total=12, spawn=1, first_stdout=2, execution=10, parse=0)
        )


def main() -> None:
    # Patch only the backend factory used by SubApiClient. This keeps the public
    # API path realistic while avoiding network access, subscriptions, or CLI auth.
    with patch("sub_api.core.client.get_backend", lambda name, timeout: FakeBackend(timeout)):
        client = SubApiClient()

        # The simplest API returns a plain string.
        direct = client.call(prompt="Hello", backend="gemini")
        assert direct == "fake response (default): Hello"

        # Direct library usage can pass backend and backend-specific model
        # separately. This is the preferred API for Python code.
        detailed = client.call(prompt="Hello", backend="gemini", model="gemini-2.5-pro")
        assert detailed == "fake response (gemini-2.5-pro): Hello"

        # The OpenAI-style API returns a response object with choices/message.
        # Internally, messages are serialized to a single prompt string.
        response = client.chat.completions.create(
            model="gemini/gemini-2.5-pro",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert response.model == "gemini/gemini-2.5-pro"
        assert (
            response.choices[0].message.content
            == "fake response (gemini-2.5-pro): user: Hello"
        )
        assert response.sub_api is not None
        assert response.sub_api["latency_ms"]["total"] >= 0
        assert response.sub_api["latency_ms"]["queued"] >= 0
        assert response.sub_api["latency_ms"]["spawn"] == 1
        assert response.usage == {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        }
        assert response.sub_api["usage"]["source"] == "heuristic"

        # Direct library usage limits same-backend concurrency by default. With a
        # single slot per backend, concurrent calls to the same backend are
        # serialized, and the second call records queue wait time in latency.queued.
        limited_client = SubApiClient()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(limited_client.call_result, prompt=f"slow {index}", backend="gemini")
                for index in range(2)
            ]
            limited_results = [future.result() for future in futures]

        assert all(result.latency.queued is not None for result in limited_results)
        assert max(result.latency.queued or 0 for result in limited_results) > 0

        # Streaming returns OpenAI-style chunks when stream=True.
        chunks = list(
            client.chat.completions.create(
                model="gemini/gemini-2.5-pro",
                messages=[{"role": "user", "content": "Hello"}],
                stream=True,
            )
        )
        assert chunks[0].choices[0].delta.role == "assistant"
        assert chunks[-1].choices[0].finish_reason == "stop"
        streamed_text = "".join(
            chunk.choices[0].delta.content or "" for chunk in chunks
        )
        assert streamed_text == "fake stream (gemini-2.5-pro): user: Hello"
        assert chunks[-1].usage == {
            "prompt_tokens": 3,
            "completion_tokens": 11,
            "total_tokens": 14,
        }
        assert chunks[-1].sub_api is not None
        assert chunks[-1].sub_api["latency_ms"]["total"] >= 0
        assert chunks[-1].sub_api["usage"]["source"] == "heuristic"

        # Direct streaming can expose stats after the iterator is exhausted.
        stream_result = client.stream_result(prompt="Hello", backend="gemini")
        assert "".join(stream_result.chunks) == "fake stream (default): Hello"
        assert stream_result.result is not None
        assert stream_result.result.usage.source == "heuristic"

    # A short success message keeps this script useful in CI or quick local checks.
    print("direct client smoke test passed")


if __name__ == "__main__":
    main()
