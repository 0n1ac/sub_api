from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    default_backend: str = "gemini"
    timeout: float = 60.0
    host: str = "127.0.0.1"
    port: int = 8000
    server_max_concurrent_per_backend: int = 1
    concurrency_queue_timeout: float | None = None


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        default_backend=os.getenv("DEFAULT_BACKEND", "gemini").lower(),
        timeout=float(os.getenv("TIMEOUT", "60")),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        server_max_concurrent_per_backend=int(
            os.getenv("SUB_API_SERVER_MAX_CONCURRENT_PER_BACKEND", "1")
        ),
        concurrency_queue_timeout=_optional_float(os.getenv("SUB_API_CONCURRENCY_QUEUE_TIMEOUT")),
    )


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
