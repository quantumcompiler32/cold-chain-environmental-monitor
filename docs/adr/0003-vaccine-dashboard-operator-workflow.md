# ADR-0003: Vaccine dashboard centers operator response

## Status

Accepted

## Decision

The vaccine dashboard will prioritize an operator's response to a temperature excursion. It will connect storage-unit telemetry to synthetic affected-stock and disposition information, while keeping raw events and research provenance secondary.

The dashboard will use `Demo simulation` labeling for conference-safe scenarios. It will not automate clinical release decisions.

## Rationale

Temperature events alone are difficult to act on. Linking an excursion to affected stock, ownership, notes, and disposition makes the system's operational purpose clear without overstating the prototype's clinical authority.

The vocabulary and provenance fields follow the temperature IoT project's event model: device, sensor, vaccine profile, scenario, Celsius temperature, status, and source timestamp.
