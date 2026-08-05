"""Consistent human-readable terminal output for the live demo backend."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

try:
    from backend.event_contract import format_timestamp, parse_timestamp
except ImportError:  # pragma: no cover - keeps direct script execution working.
    from event_contract import format_timestamp, parse_timestamp


CALIFORNIA_TIMEZONE = ZoneInfo("America/Los_Angeles")


def _value(value: Any) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, datetime):
        return format_timestamp(value)
    return str(value)


def _temperature(value: Any) -> str:
    if value in (None, ""):
        return "-"
    return f"{float(value):.2f} °C"


def _california_timestamp(value: Any) -> str:
    """Display event lifecycle timestamps in the operator's Pacific timezone."""
    if value in (None, ""):
        return "-"
    timestamp = parse_timestamp(value, "timestamp", assume_utc=True)
    local = timestamp.astimezone(CALIFORNIA_TIMEZONE)
    return local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + f" {local.tzname()}"


def format_event_block(
    event: dict[str, Any],
    *,
    component: str,
    outcome: str,
    sequence: int | None = None,
    topic: str | None = None,
    received_at: datetime | None = None,
    stored_at: datetime | None = None,
) -> str:
    """Format one event consistently for generator and listener terminals."""
    title = f"[{component}] {outcome}"
    if sequence is not None:
        title += f" #{sequence:04d}"

    scenario = _value(event.get("scenario"))
    phase = event.get("scenario_phase")
    lines = [
        title,
        f"  event_id      : {_value(event.get('event_id'))}",
        f"  run_id        : {_value(event.get('run_id'))}",
        f"  device        : {_value(event.get('device_id'))}",
        f"  pod           : {_value(event.get('sensor_name'))}",
        f"  vaccine       : {_value(event.get('vaccine_type'))}",
        f"  scenario      : {scenario}",
        f"  phase         : {_value(phase)}",
        f"  occupancy     : {_value(event.get('occupancy_state'))}",
        f"  batch         : {_value(event.get('batch_id'))}",
        f"  temperature   : {_temperature(event.get('temperature_c'))}",
        f"  safe_range    : {_temperature(event.get('storage_min_c'))} to {_temperature(event.get('storage_max_c'))}",
        f"  status        : {_value(event.get('status'))}",
        f"  pod_status    : {_value(event.get('operational_status'))}",
        f"  severity      : {_value(event.get('severity'))}",
        f"  alert         : {_value(event.get('rule_alert'))}",
        f"  uncertainty   : {_value(event.get('uncertainty_status'))}",
        f"  boundary      : {_value(event.get('boundary_crossing'))}",
        f"  event_time    : {_california_timestamp(event.get('event_time'))}",
    ]
    if topic is not None:
        lines.append(f"  topic         : {topic}")
    if received_at is not None:
        lines.append(f"  received_at   : {_california_timestamp(received_at)}")
    if stored_at is not None:
        lines.append(f"  stored_at     : {_california_timestamp(stored_at)}")
    return "\n".join(lines)


def format_service_message(component: str, message: str) -> str:
    """Format a one-line lifecycle/status message."""
    return f"[{component}] {message}"
