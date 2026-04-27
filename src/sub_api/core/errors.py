from __future__ import annotations


class SubApiError(RuntimeError):
    """Base exception for sub_api failures."""


class BackendNotAvailable(SubApiError):
    """Raised when a requested backend CLI is not installed or not on PATH."""


class BackendTimeout(SubApiError):
    """Raised when a backend CLI exceeds the configured timeout."""


class BackendExecutionError(SubApiError):
    """Raised when a backend CLI exits unsuccessfully or returns unusable output."""
