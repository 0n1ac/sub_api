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


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        default_backend=os.getenv("DEFAULT_BACKEND", "gemini").lower(),
        timeout=float(os.getenv("TIMEOUT", "60")),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
