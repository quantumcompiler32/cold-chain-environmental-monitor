# Database access contract

This document is the source of truth for which process reads or writes
PostgreSQL. The browser never receives database credentials.

## Event identity and projections

- `event_id` identifies one measurement and is unique in both application
  tables. It is the correlation key used by PostgreSQL `NOTIFY`, the API, the
  raw payload, and the browser's event map.
- `run_id` is optional correlation metadata shared by events emitted in one
  generator run. It is not a uniqueness key and may be `NULL` for legacy
  events.
- `telemetry_logs` is the generic raw projection. It keeps the JSON payload,
  device, topic, temperature, status, and lifecycle timestamps.
- `vaccine_temperature_events` is the vaccine-domain projection. It stores the
  flattened fields used by dashboard filters and analytics.
- The two tables are intentional, not two independent event stores. The
  domain row has a foreign key to the raw row, and `persist_event()` inserts
  both projections in one transaction. A transaction that cannot leave both
  rows present is rolled back; a duplicate is reported only when both rows
  already exist.

## Read/write ledger

| Component | Reads | Writes | Mode and purpose |
| --- | --- | --- | --- |
| `services.temperature_event_generator` | Bundled CSV guidance | None by default; both projections only with explicit `--write-db` | Default mode publishes to MQTT. Direct mode is mutually exclusive with MQTT publishing so one event is not written twice. |
| `services.temperature_subscriber` | Table existence and domain count at startup | `telemetry_logs`, `vaccine_temperature_events`, and transactional `pg_notify` | `--write-db` is the normal production/demo write owner. Validation happens before the transaction. |
| `services.dashboard_bridge.DatabaseReader` | `vaccine_temperature_events`; schema readiness query; PostgreSQL `LISTEN` notifications | None | Every data connection uses `SET TRANSACTION READ ONLY`. Notifications trigger reads; they do not contain the event record. |
| `scripts/verify_database.py` | Both application tables and projection parity | None | Fast, read-only readiness/parity probe. |
| `scripts/verify_persistence.py` | `vaccine_temperature_events` | None | Detailed latest-event and lifecycle-timestamp report. |
| `scripts/reset_demo.py` | Environment and target settings | Drops/recreates application tables and sends reset notification | Destructive and guarded by local-host, non-production, and explicit-confirmation checks. |
| `scripts/reset_dashboard.py` | Target settings | Transactional `pg_notify` on the dashboard-reset channel only | Clears open dashboard memory; it does not delete or rewrite event rows. |
| `services.ml_inference` | Model artifacts supplied on disk | None | Inference is advisory and does not read or mutate PostgreSQL. |
| SQL bootstrap/migrations | Existing schema/data as required by migration | Schema changes and legacy backfill | Run as an explicit database-administration operation, never from the dashboard bridge. |

## API behavior

The bridge is a read-only API:

- `GET /health` is liveness only and remains `200` when PostgreSQL is down.
- `GET /ready` (also `/api/ready` and `/api/health`) checks PostgreSQL and the
  canonical tables; it returns `200` when ready and `503` otherwise.
- `GET /api/events`, `/api/live`, `/api/live/stream`, `/api/analytics`, and
  `/api/events/export.csv` read persisted domain rows.
- `POST`, `PUT`, `PATCH`, and `DELETE` return `405` with `Allow: GET,
  OPTIONS`. There is no dashboard write endpoint.
- `/` and `/api` return route discovery. A page URL such as
  `/pages/domain-vaccine.html` belongs to the website server on port `8766`,
  not the API server on port `8787`; the bridge returns a diagnostic `404`
  with that explanation.
- The ML service uses the same liveness/readiness distinction on port `5000`:
  `/health` reports process/model state and `/ready` returns `503` until model
  artifacts are loaded.

Every HTTP request gets an `X-Request-ID` response header. Error bodies and
service logs include that ID so a browser error can be matched to a server
diagnostic. Persistence logs include `event_id` and `run_id` when available.
