# Data dictionary

The event contract is shared by the generator, listener, database, bridge, and
dashboard. Use the names below when writing tests, reports, or presentation
notes. The full database shape is defined by
[database/bootstrap/001_core.sql](../database/bootstrap/001_core.sql).

## Event fields

| Field | Type / example | Meaning and source |
| --- | --- | --- |
| `event_id` | UUID | Stable identity generated for one simulated reading. It is the raw-table unique key and domain-table primary key. |
| `run_id` | nullable string | Correlation ID shared by all events emitted by one generator run. It is diagnostic metadata, not a uniqueness key. Legacy events may leave it null. |
| `device_id` | string | Simulated device identity, currently `vaccine_temperature_simulator`. |
| `sensor_name` | string, `Pod1` | Pod/channel name. A Pod is a simulated sensor channel, not a storage unit. |
| `vaccine_type` | string, `pfizer_ultralow` | Selected vaccine profile used for classification. |
| `scenario` | enum | Requested control: `normal`, `warning`, `recovery`, `mixed`, or `outlier`. |
| `scenario_phase` | nullable enum | Phase inside `mixed`: `normal`, `cooling_failure`, or `recovery`. Other scenarios leave this null. |
| `occupancy_state` | enum | `loaded`, `empty`, or `offline`. |
| `batch_id` | nullable string | Demo batch correlation key. The E2E verifier puts its run ID here; it is not a clinical lot decision. |
| `cooling_enabled` | boolean | Whether cooling is enabled for the simulated Pod. |
| `operational_status` | enum | Derived Pod state: `NORMAL`, `WARNING`, `CRITICAL`, `STALE`, `RECOVERY`, `SENSOR_FAULT`, `EMPTY`, `ENERGY_WASTE`, or `OFFLINE`. `STALE` means the event timestamp is older than five minutes at ingestion; `RECOVERY` means an in-range recovery-phase reading. |
| `severity` | enum | Derived attention level: `info`, `warning`, or `critical`. |
| `rule_alert` | nullable string | Derived rule such as `VACCINE_SAFE_RANGE_VIOLATION`, `TEMPERATURE_BOUNDARY_RISK`, `POD_OFFLINE`, or `EMPTY_POD_COOLING`. |
| `temperature_c` | decimal | Observed reading in Celsius. The source CSV's Fahrenheit value is converted before scenario logic. |
| `status` | enum | Temperature classification: `STABLE`, `ACCEPTABLE`, `TOO_COLD`, `TOO_WARM`, or `SENSOR_FAULT`. |
| `sensor_tolerance_c` | decimal, `0.5` | Sensor uncertainty used to derive the possible interval. |
| `temperature_min_possible_c` | decimal | Observed temperature minus sensor tolerance. |
| `temperature_max_possible_c` | decimal | Observed temperature plus sensor tolerance. |
| `storage_min_c` | decimal | Lower bound for the selected profile. |
| `storage_max_c` | decimal | Upper bound for the selected profile. |
| `uncertainty_status` | string | Whether the possible interval is within range, crosses a boundary, or is outside the range. |
| `boundary_crossing` | boolean | True when sensor uncertainty overlaps a storage boundary. It does not change the raw `status`. |
| `measurement_confidence` | string | Human-readable provenance for the sensor tolerance. |
| `event_time` | UTC timestamp | When the simulator created the event. |
| `received_at` | UTC timestamp | When the MQTT listener received the event. |
| `stored_at` | UTC timestamp | When PostgreSQL completed persistence. |
| `timestamp` | legacy wire alias | Compatibility alias for `event_time`; new consumers should use `event_time`. |

## Derived verification fields

The bridge adds these presentation-only values to API responses:

| Field | Meaning |
| --- | --- |
| `ingestion_latency_ms` | `received_at - event_time` in milliseconds. |
| `event_age_seconds` | Current time minus `event_time` at query time. It is expected to change between reads. |
| `scope` | API response metadata describing filters and effective time bounds. |

## Table boundaries

`telemetry_logs` stays generic: event identity, device, topic, event time, raw
JSON payload, generic sensor values, status, and lifecycle timestamps.
`vaccine_temperature_events` owns the vaccine-specific interpretation and
operational fields. Do not add vaccine columns to the generic raw table.
