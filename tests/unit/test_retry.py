# pyright: strict
"""Tests for failure/retry.py primitives."""

from __future__ import annotations

import time

import pytest

from lem.failure.retry import exponential_backoff, parse_retry_after


def test_exponential_backoff_growth() -> None:
    assert exponential_backoff(attempt=1) == pytest.approx(5.0)
    assert exponential_backoff(attempt=2) == pytest.approx(10.0)
    assert exponential_backoff(attempt=3) == pytest.approx(20.0)


def test_exponential_backoff_capped() -> None:
    assert exponential_backoff(attempt=10) == pytest.approx(60.0)
    assert exponential_backoff(attempt=100) == pytest.approx(60.0)


def test_parse_retry_after_seconds() -> None:
    assert parse_retry_after("30") == pytest.approx(30.0)


def test_parse_retry_after_http_date() -> None:
    future = time.time() + 120.0
    import email.utils
    http_date = email.utils.formatdate(future, usegmt=True)
    result = parse_retry_after(http_date)
    assert result is not None
    assert 115.0 < result < 125.0


def test_parse_retry_after_invalid() -> None:
    assert parse_retry_after("not-a-date-or-number") is None


def test_parse_retry_after_absent() -> None:
    assert parse_retry_after(None) is None
