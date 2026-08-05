#!/usr/bin/env python3
"""Shared Type-T thermocouple uncertainty helpers.

The paper supplied for this project describes approximately +/-0.5 C accuracy
for the Type-T thermocouples.  These helpers keep that measurement uncertainty
separate from the vaccine storage range and never replace the raw reading.
"""

from __future__ import annotations

import math
from typing import Any


# This is sensor measurement accuracy from the paper, not vaccine storage
# tolerance.  Keep the name explicit so it is not confused with a profile's
# acceptable minimum and maximum.
SENSOR_TOLERANCE_C = 0.5
MEASUREMENT_CONFIDENCE = "Approximately +/-0.5 C Type-T thermocouple accuracy"


def _finite(value: Any, field_name: str) -> float:
    """Convert a value to a finite float or raise a useful validation error."""
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{field_name} must be finite.")
    return converted


def possible_temperature_range(
    temperature_c: Any,
    tolerance_c: Any = SENSOR_TOLERANCE_C,
) -> tuple[float, float]:
    """Return the possible measured range without changing the raw value."""
    temperature = _finite(temperature_c, "temperature_c")
    tolerance = _finite(tolerance_c, "sensor_tolerance_c")
    if tolerance < 0:
        raise ValueError("sensor_tolerance_c cannot be negative.")
    return (
        round(temperature - tolerance, 2),
        round(temperature + tolerance, 2),
    )


def classify_uncertainty(
    temperature_c: Any,
    storage_min_c: Any,
    storage_max_c: Any,
    tolerance_c: Any = SENSOR_TOLERANCE_C,
) -> dict[str, Any]:
    """Describe whether the uncertainty interval crosses a storage boundary.

    The original status remains the authoritative raw classification.  This
    additional interpretation only says how confidently that classification can
    be read when the +/-0.5 C sensor uncertainty is considered.
    """
    temperature = _finite(temperature_c, "temperature_c")
    lower = _finite(storage_min_c, "storage_min_c")
    upper = _finite(storage_max_c, "storage_max_c")
    if lower >= upper:
        raise ValueError("storage_min_c must be less than storage_max_c.")
    tolerance = _finite(tolerance_c, "sensor_tolerance_c")
    possible_min, possible_max = possible_temperature_range(temperature, tolerance)

    crosses_lower = possible_min < lower <= possible_max
    crosses_upper = possible_min <= upper < possible_max
    if crosses_lower and crosses_upper:
        uncertainty_status = "BORDERLINE_RANGE"
    elif crosses_lower:
        uncertainty_status = "BORDERLINE_COLD"
    elif crosses_upper:
        uncertainty_status = "BORDERLINE_WARM"
    elif possible_max < lower:
        uncertainty_status = "CLEARLY_TOO_COLD"
    elif possible_min > upper:
        uncertainty_status = "CLEARLY_TOO_WARM"
    else:
        uncertainty_status = "WITHIN_RANGE"

    return {
        "sensor_tolerance_c": round(tolerance, 2),
        "temperature_min_possible_c": possible_min,
        "temperature_max_possible_c": possible_max,
        "storage_min_c": round(lower, 2),
        "storage_max_c": round(upper, 2),
        "uncertainty_status": uncertainty_status,
        "boundary_crossing": crosses_lower or crosses_upper,
        "measurement_confidence": MEASUREMENT_CONFIDENCE,
    }


def enrich_event(
    event: dict[str, Any],
    storage_min_c: Any,
    storage_max_c: Any,
) -> dict[str, Any]:
    """Add or replace uncertainty fields on an event while preserving its value."""
    enriched = dict(event)
    enriched.update(
        classify_uncertainty(
            enriched.get("temperature_c"),
            storage_min_c,
            storage_max_c,
            enriched.get("sensor_tolerance_c", SENSOR_TOLERANCE_C),
        )
    )
    return enriched
