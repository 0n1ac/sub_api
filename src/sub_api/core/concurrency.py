from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from sub_api.core.errors import BackendConcurrencyTimeout


@dataclass(frozen=True)
class ConcurrencySlot:
    backend: str
    queued_ms: int


class BackendConcurrencyLimiter:
    def __init__(self, max_concurrent_per_backend: int | None) -> None:
        if max_concurrent_per_backend is not None and max_concurrent_per_backend < 1:
            raise ValueError("max_concurrent_per_backend must be >= 1 or None.")

        self.max_concurrent_per_backend = max_concurrent_per_backend
        self._lock = threading.Lock()
        self._semaphores: dict[str, threading.BoundedSemaphore] = {}

    @contextmanager
    def acquire(self, backend: str, timeout: float | None) -> Iterator[ConcurrencySlot]:
        if self.max_concurrent_per_backend is None:
            yield ConcurrencySlot(backend=backend, queued_ms=0)
            return

        semaphore = self._get_semaphore(backend)
        wait_start = time.perf_counter()
        if timeout is None:
            acquired = semaphore.acquire()
        else:
            acquired = semaphore.acquire(timeout=timeout)
        queued_ms = _elapsed_ms(wait_start)

        if not acquired:
            raise BackendConcurrencyTimeout(
                f"Timed out waiting for an available {backend} backend slot."
            )

        try:
            yield ConcurrencySlot(backend=backend, queued_ms=queued_ms)
        finally:
            semaphore.release()

    def _get_semaphore(self, backend: str) -> threading.BoundedSemaphore:
        with self._lock:
            semaphore = self._semaphores.get(backend)
            if semaphore is None:
                assert self.max_concurrent_per_backend is not None
                semaphore = threading.BoundedSemaphore(self.max_concurrent_per_backend)
                self._semaphores[backend] = semaphore
            return semaphore


def _elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))
