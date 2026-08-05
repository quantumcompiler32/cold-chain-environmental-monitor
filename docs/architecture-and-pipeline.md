# Architecture and pipeline

This repository is a local, synthetic cold-chain monitoring demonstration. It
is designed to make the full evidence path visible:

```text
source CSV guidance
        |
        v
temperature_event_generator --scenario ...
        |
        v
Mosquitto: devices/temperature
        |
        v
temperature_subscriber --write-db
        |
        +--> telemetry_logs                  (generic raw event)
        |
        +--> vaccine_temperature_events     (flattened domain event)
        |
        v
dashboard_bridge (read-only HTTP + SSE)
        |
        v
browser dashboard / verification client
```

## Component responsibilities

| Component | Responsibility | Boundary |
| --- | --- | --- |
| `backend/temperature_event_generator.py` | Reads source temperature variation, applies a named scenario, builds the event contract, and publishes MQTT messages. | CLI and `devices/temperature` MQTT topic |
| Mosquitto | Transports messages locally. | MQTT on `localhost:1883` |
| `backend/temperature_subscriber.py` | Validates the event, stamps ingestion time, and performs the atomic dual write. | MQTT consumer and PostgreSQL transaction |
| `telemetry_logs` | Retains generic raw JSON and transport facts. | PostgreSQL table |
| `vaccine_temperature_events` | Stores vaccine-specific fields used by the dashboard. | PostgreSQL table, keyed by `event_id` |
| `backend/dashboard_bridge.py` | Serves committed events and analytics without write access. | HTTP on `localhost:8787`, plus SSE |
| `frontend/` | Displays the read-only bridge responses. | Browser client |

The generator's CSV is guidance for source variation only. It does not provide
the live event timestamp. `event_time` is created when the event is generated;
`received_at` is created by the listener; and `stored_at` is created when the
PostgreSQL transaction completes. All three are UTC `TIMESTAMPTZ` values in the
database and millisecond-precision ISO-8601 values on the wire/presentation
boundaries.

## Persistence contract

The subscriber normalizes and validates one event, then inserts the generic and
vaccine rows in one transaction. `event_id` is unique in `telemetry_logs` and
is the primary key/foreign key on `vaccine_temperature_events`. A duplicate is
reported as idempotent and does not create a second domain row. A PostgreSQL
notification is sent only after the transaction commits, so the live dashboard
does not receive a rolled-back event. `run_id` groups events from one generator
invocation for diagnostics; `event_id` remains the identity of one reading.

The clean schema is [db/bootstrap/001_core.sql](../db/bootstrap/001_core.sql).
Schema changes belong in [db/migrations/](../db/migrations/), not in
the clean bootstrap path.

## Read-only dashboard contract

The bridge's stable public endpoints are:

```text
GET /health
GET /api/events
GET /api/live
GET /api/verification/latest-events
GET /api/analytics
GET /api/events/export.csv
GET /api/live/stream
```

Supported filters include `pod`, `vaccine`, `batch`, `scenario`, `severity`,
`occupancy`, `start`, and `end`. `POST` is rejected. The bridge uses a
PostgreSQL read-only transaction for each request and never starts the
generator, listens to MQTT, writes events, or changes disposition.

## Operating principles

- Operational monitoring and exceptions come before trends or ML assistance.
- All Pods are the default dashboard scope.
- A demo is synthetic and must be labelled `Demo simulation`.
- ML inference is separate, advisory, explicitly trained, and read-only.
- Event status and affected-stock disposition are different decisions; this
  demo does not automatically release or quarantine stock.
