# pyright: strict
"""Exponential backoff for 429/5xx, schema retry.

NOTE: CLI-mode v1 limitation — the claude CLI conflates all error types into a
non-zero exit code. Detecting HTTP 429 or 5xx specifically is not possible in
CLI mode. The primitives here are implemented for v1.1+ SDK-mode workers that
surface HTTP status codes directly. In CLI mode, dispatch.py performs
retry-once-on-non-zero-exit without HTTP-aware backoff.
"""

from __future__ import annotations

import time
from email.utils import parsedate_to_datetime


def exponential_backoff(
    *,
    attempt: int,
    base_s: float = 5.0,
    factor: float = 2.0,
    max_s: float = 60.0,
) -> float:
    """Return seconds to sleep before retry attempt N (1-indexed).

    attempt=1 → base_s, attempt=2 → base_s*factor, capped at max_s.
    """
    delay = base_s * (factor ** (attempt - 1))
    return min(delay, max_s)


def parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header (delta-seconds OR HTTP-date).

    Returns seconds to wait, or None if absent or unparseable.
    """
    if value is None:
        return None
    stripped = value.strip()
    try:
        return float(stripped)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(stripped)
        delta = dt.timestamp() - time.time()
        return max(0.0, delta)
    except Exception:
        return None
