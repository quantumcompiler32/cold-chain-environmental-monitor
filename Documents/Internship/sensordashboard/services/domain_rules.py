"""Domain rules shared by ingestion and presentation adapters."""

from __future__ import annotations

from typing import Any


OCCUPANCY_STATES = ("loaded", "empty", "offline")
OPERATIONAL_STATUSES = ("NORMAL", "WARNING", "CRITICAL", "SENSOR_FAULT", "EMPTY", "ENERGY_WASTE", "OFFLINE")
SEVERITIES = ("info", "warning", "critical")


def normalize_occupancy(value: Any) -> str:
    state = str(value or "loaded").strip().lower()
    if state not in OCCUPANCY_STATES:
        raise ValueError(f"occupancy_state must be one of: {', '.join(OCCUPANCY_STATES)}")
    return state


def derive_operational_state(event: dict[str, Any]) -> dict[str, Any]:
    """Derive pod status and rule alerts from observed event facts."""
    occupancy = normalize_occupancy(event.get("occupancy_state"))
    cooling_enabled = bool(event.get("cooling_enabled", True))
    observed_status = str(event.get("status") or "UNKNOWN")
    boundary_crossing = bool(event.get("boundary_crossing", False))
    batch_id = event.get("batch_id") or None

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
    return {
        "occupancy_state": occupancy,
        "cooling_enabled": cooling_enabled,
        "operational_status": "NORMAL",
        "severity": "info",
        "rule_alert": None,
    }
