from __future__ import annotations

import argparse
import sys

from sub_api import BackendExecutionError, BackendNotAvailable, BackendTimeout, SubApiClient


def main() -> int:
    # This example intentionally avoids the HTTP server. It shows the shortest
    # path from a user prompt to the local backend CLI through SubApiClient.
    parser = argparse.ArgumentParser(
        description="Call sub_api directly as a Python library without running the HTTP server."
    )
    parser.add_argument("prompt", nargs="?", help="Prompt text. Reads stdin when omitted.")
    parser.add_argument("--backend", default=None, choices=("gemini", "claude", "codex"))
    parser.add_argument(
        "--model",
        default=None,
        help="Optional backend-specific model name, e.g. gemini-2.5-pro or sonnet.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--stats", action="store_true", help="Print latency stats to stderr.")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print chunks as they arrive when the selected backend supports streaming stdout.",
    )
    args = parser.parse_args()

    # Accept either a positional prompt:
    #   python examples/direct_call.py "Hello" --backend gemini
    # or piped stdin:
    #   echo "Hello" | python examples/direct_call.py --backend claude --model sonnet
    prompt = args.prompt if args.prompt is not None else sys.stdin.read().strip()
    if not prompt:
        print("프롬프트가 비어 있습니다.", file=sys.stderr)
        return 2

    # SubApiClient is the library-first entry point. It calls the selected CLI
    # directly as a subprocess, so no FastAPI/Uvicorn server is involved.
    client = SubApiClient(timeout=args.timeout)

    try:
        if args.stream:
            # Streaming still uses the same backend/model selection path. Some
            # CLIs only emit stdout after the final answer; those backends fall
            # back to printing one final chunk.
            stream_result = client.stream_result(
                prompt=prompt,
                backend=args.backend,
                model=args.model,
                timeout=args.timeout,
            )
            for chunk in stream_result.chunks:
                print(chunk, end="", flush=True)
            print()
            if args.stats and stream_result.result is not None:
                print(f"latency_ms={stream_result.result.latency.as_dict()}", file=sys.stderr)
                print(
                    "usage="
                    f"{stream_result.result.usage.as_openai_usage()} "
                    f"source={stream_result.result.usage.source}",
                    file=sys.stderr,
                )
            return 0

        result = client.call_result(
            prompt=prompt,
            backend=args.backend,
            model=args.model,
            timeout=args.timeout,
        )
    except BackendNotAvailable as exc:
        # Usually means the selected CLI is not installed or not available on PATH.
        print(f"백엔드를 사용할 수 없습니다: {exc}", file=sys.stderr)
        return 1
    except BackendTimeout as exc:
        # The CLI process exceeded --timeout seconds and was terminated.
        print(f"백엔드 호출 시간이 초과되었습니다: {exc}", file=sys.stderr)
        return 1
    except BackendExecutionError as exc:
        # Covers non-zero CLI exits and output parsing failures.
        print(f"백엔드 실행에 실패했습니다: {exc}", file=sys.stderr)
        return 1

    # call_result returns assistant text plus runtime metadata.
    # Use client.call(...) if you only need the plain assistant text.
    print(result.content)
    if args.stats:
        print(f"latency_ms={result.latency.as_dict()}", file=sys.stderr)
        print(
            f"usage={result.usage.as_openai_usage()} source={result.usage.source}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
