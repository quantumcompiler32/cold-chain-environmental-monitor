"""Domain rules shared by ingestion and presentation adapters.

The subscriber persists the returned operational state with each raw event.
An event older than ``STALE_AFTER_SECONDS`` is stale even if its measured
temperature was safe; an in-range recovery event remains visibly in recovery
until the next normal reading. These rules make warning, critical, stale, and
recovery evidence explicit in PostgreSQL and the read-only dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


OCCUPANCY_STATES = ("loaded", "empty", "offline")
STALE_AFTER_SECONDS = 300
OPERATIONAL_STATUSES = (
    "NORMAL", "WARNING", "CRITICAL", "STALE", "RECOVERY",
    "SENSOR_FAULT", "EMPTY", "ENERGY_WASTE", "OFFLINE",
)
SEVERITIES = ("info", "warning", "critical")


def normalize_occupancy(value: Any) -> str:
    state = str(value or "loaded").strip().lower()
    if state not in OCCUPANCY_STATES:
        raise ValueError(f"occupancy_state must be one of: {', '.join(OCCUPANCY_STATES)}")
    return state


def _event_age_seconds(event: dict[str, Any], now: datetime | None) -> float | None:
    """Return event age for stale detection, or ``None`` for invalid/missing time."""
    value = event.get("event_time") or event.get("timestamp")
    if isinstance(value, datetime):
        event_time = value
    elif isinstance(value, str) and value.strip():
        try:
            event_time = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0.0, (reference - event_time).total_seconds())


def derive_operational_state(event: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Derive pod status and rule alerts from observed event facts and age."""
    occupancy = normalize_occupancy(event.get("occupancy_state"))
    cooling_enabled = bool(event.get("cooling_enabled", True))
    observed_status = str(event.get("status") or "UNKNOWN")
    boundary_crossing = bool(event.get("boundary_crossing", False))
    batch_id = event.get("batch_id") or None
    scenario = str(event.get("scenario") or "")
    scenario_phase = str(event.get("scenario_phase") or "")

    # A delayed event is a data-freshness incident. It is checked before
    # temperature classification so an old safe reading cannot look current.
    age_seconds = _event_age_seconds(event, now)
    if age_seconds is not None and age_seconds > STALE_AFTER_SECONDS:
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "STALE",
            "severity": "critical",
            "rule_alert": "EVENT_STALE",
        }

    if occupancy == "offline":
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "OFFLINE",
            "severity": "critical",
            "rule_alert": "POD_OFFLINE",
        }
    if occupancy == "empty":
        if cooling_enabled:
            return {
                "occupancy_state": occupancy,
                "cooling_enabled": cooling_enabled,
                "operational_status": "ENERGY_WASTE",
                "severity": "warning",
                "rule_alert": "EMPTY_POD_COOLING",
            }
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "EMPTY",
            "severity": "info",
            "rule_alert": None,
        }
    if observed_status == "SENSOR_FAULT":
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "SENSOR_FAULT",
            "severity": "critical",
            "rule_alert": "SENSOR_FAULT",
        }
    if observed_status in {"TOO_COLD", "TOO_WARM"}:
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "CRITICAL",
            "severity": "critical",
            "rule_alert": "VACCINE_SAFE_RANGE_VIOLATION",
        }
    if not batch_id:
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "WARNING",
            "severity": "warning",
            "rule_alert": "LOADED_POD_NO_BATCH",
        }
    if boundary_crossing:
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "WARNING",
            "severity": "warning",
            "rule_alert": "TEMPERATURE_BOUNDARY_RISK",
        }
    if scenario == "recovery" or scenario_phase == "recovery":
        return {
            "occupancy_state": occupancy,
            "cooling_enabled": cooling_enabled,
            "operational_status": "RECOVERY",
            "severity": "warning",
            "rule_alert": "TEMPERATURE_RECOVERY",
        }
    return {
        "occupancy_state": occupancy,
        "cooling_enabled": cooling_enabled,
        "operational_status": "NORMAL",
        "severity": "info",
        "rule_alert": None,
    }
