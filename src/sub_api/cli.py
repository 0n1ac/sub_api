from __future__ import annotations

import argparse
import importlib.metadata
import sys

from sub_api import BackendExecutionError, BackendNotAvailable, BackendTimeout, SubApiClient
from sub_api.core.backends import BACKENDS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sub_api")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Ask a backend once.")
    ask_parser.add_argument("prompt", nargs="?", help="Prompt text. Reads stdin when omitted.")
    ask_parser.add_argument("--model", default="gemini", choices=sorted(BACKENDS))
    ask_parser.add_argument("--timeout", type=float, default=None)

    serve_parser = subparsers.add_parser("serve", help="Run the OpenAI-compatible HTTP server.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true")

    subparsers.add_parser("status", help="Show backend availability.")
    subparsers.add_parser("version", help="Show sub_api version.")

    args = parser.parse_args(argv)

    if args.command == "ask":
        return cmd_ask(args)
    if args.command == "serve":
        return cmd_serve(args)
    if args.command == "status":
        return cmd_status()
    if args.command == "version":
        return cmd_version()

    parser.print_help()
    return 1


def cmd_ask(args: argparse.Namespace) -> int:
    prompt = args.prompt if args.prompt is not None else sys.stdin.read().strip()
    if not prompt:
        print("프롬프트가 비어 있습니다.", file=sys.stderr)
        return 2

    client = SubApiClient(timeout=args.timeout)
    try:
        print(client.call(model=args.model, prompt=prompt, timeout=args.timeout))
    except (BackendExecutionError, BackendNotAvailable, BackendTimeout) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
        from sub_api.server.main import app
    except ImportError:
        print(
            "서버 모드를 사용하려면 다음을 설치하세요:\n"
            "  pip install sub_api[server]",
            file=sys.stderr,
        )
        return 1

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_status() -> int:
    client = SubApiClient()
    versions = client.backend_versions()

    for name in BACKENDS:
        version = versions[name]
        if version is None:
            print(f"{name:<7} x not installed")
        else:
            print(f"{name:<7} available ({version})")
    return 0


def cmd_version() -> int:
    try:
        version = importlib.metadata.version("sub_api")
    except importlib.metadata.PackageNotFoundError:
        version = "0.2.0"
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
