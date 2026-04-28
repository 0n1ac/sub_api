from __future__ import annotations

from unittest.mock import patch

from sub_api import SubApiClient
from sub_api.core.backends.base import BackendResult


class FakeBackend:
    # This fake backend mirrors the minimal interface used by SubApiClient.
    # It lets the example run without installing or authenticating any real CLI.
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def call(self, prompt: str, model: str | None = None) -> BackendResult:
        # Real backends return BackendResult(content=...) after subprocess output
        # has been parsed. The fake response keeps assertions deterministic.
        model_label = model or "default"
        return BackendResult(content=f"fake response ({model_label}): {prompt}")


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

    # A short success message keeps this script useful in CI or quick local checks.
    print("direct client smoke test passed")


if __name__ == "__main__":
    main()
