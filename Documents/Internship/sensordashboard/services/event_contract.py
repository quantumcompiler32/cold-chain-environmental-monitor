"""Shared event-contract and timestamp helpers.

The wire format uses ISO-8601 strings. Database callers use the returned
timezone-aware ``datetime`` objects directly so PostgreSQL receives native
``TIMESTAMPTZ`` values rather than hand-built strings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


def utc_millisecond(value: datetime) -> datetime:
    """Normalize an aware datetime to UTC with millisecond precision."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    normalized = value.astimezone(timezone.utc)
    return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)


def now_utc(clock: Callable[[], datetime] | None = None) -> datetime:
    """Return the current UTC instant using an injectable clock for tests."""
    current = clock() if clock is not None else datetime.now(timezone.utc)
    return utc_millisecond(current)


def parse_timestamp(value: Any, field_name: str, *, assume_utc: bool = True) -> datetime:
    """Parse a timestamp and return an aware UTC datetime.

    Historical CSV timestamps do not carry an offset. They are treated as UTC
    for this local simulation and remain distinguishable through ``source_time``.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    else:
        raise ValueError(f"{field_name} must be a timestamp")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not assume_utc:
            raise ValueError(f"{field_name} must include a timezone")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return utc_millisecond(parsed)


def format_timestamp(value: datetime) -> str:
    """Format a wire/presentation timestamp without changing its instant."""
    return utc_millisecond(value).isoformat(timespec="milliseconds")


def human_timestamp(value: datetime) -> str:
    """Format a timestamp for a person at the presentation boundary."""
    return utc_millisecond(value).astimezone().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
