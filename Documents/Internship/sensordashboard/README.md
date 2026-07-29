# Vaccine cold-chain monitoring demo

This project is a local, synthetic vaccine cold-chain monitoring pipeline. It
simulates Pod temperature events, transports them through MQTT, validates and
persists them in PostgreSQL, and presents the persisted evidence through a
read-only dashboard adapter.

ML retraining, model deployment, and live inference are intentionally deferred
from the current implementation slice.

## Architecture and data flow

```text
CSV guidance → event generator → Mosquitto MQTT → listener
                                                   │
                                  one PostgreSQL transaction
                                     ┌─────────────┴─────────────┐
                                     │                           │
                              telemetry_logs       vaccine_temperature_events
                              generic JSON/raw       flattened vaccine rows
                                     └─────────────┬─────────────┘
                                                   │
                                      read-only dashboard bridge
                                                   │
                                                browser UI
```

- The CSV is historical guidance for source variation. It is not the time of
  the simulated event.
- The generator creates a new stable `event_id` and current UTC `event_time`.
- The listener stamps `received_at` when it ingests the MQTT message.
- The persistence transaction stamps `stored_at` and writes both tables.
- The dashboard never connects directly to PostgreSQL and never writes data.

## Timestamp fields

| Field | Meaning |
| --- | --- |
| `event_time` | Current UTC time when the simulated event is created |
| `source_time` | Optional historical CSV reading time, preserved as provenance |
| `received_at` | Current UTC time when the listener ingests the MQTT message |
| `stored_at` | Current UTC time when PostgreSQL persistence completes |

All database timestamps are timezone-aware PostgreSQL `TIMESTAMPTZ` values with
millisecond precision. Python sends timezone-aware datetime objects to the
database; it does not manually add `T` or `Z` to database values. ISO-8601
strings are used only on the event wire format and presentation boundaries.

## Prerequisites

- macOS with Homebrew
- Python 3.12+ and the bundled virtual environment or a new virtualenv
- PostgreSQL 16
- Mosquitto
- Node.js for browser data-layer tests

Install Python dependencies:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Supported environment variables:

```text
APP_ENV=development|demo|test
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=iotdb
POSTGRES_USER=<local postgres role>
POSTGRES_PASSWORD=<optional password>
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=devices/temperature
```

## Reproducible demo commands

Run each long-running command in its own terminal.

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
make start-infrastructure
APP_ENV=demo make reset-demo RESET_CONFIRM=YES
make start-listener
make run-scenario SCENARIO=normal COUNT=30 INTERVAL_MS=100 SEED=42
make verify
make start-dashboard
```

Serve the browser in another terminal:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard/web
python3 -m http.server 8765 --bind 127.0.0.1
```

Open <http://127.0.0.1:8765/index.html>.

The generator supports exactly three current user-facing scenarios:

- `normal`: translated source variation stays inside the vaccine profile range.
- `recovery`: begins above the safe range and moves back toward the profile target.
- `mixed`: deterministic normal, cooling-failure, and recovery phases.

The public CLI controls are:

```text
--scenario normal|recovery|mixed
--vaccine pfizer_ultralow|moderna
--count N
--interval-ms N
--seed N
--write-db
--output-mode none|summary|verbose
```

Summary mode is the default. It reports requested, generated, published, and
failed counts; per-phase counts; first and last event times; elapsed seconds;
and events per second. `verbose` prints each event. `none` suppresses normal
per-event output for large runs.

## Database design

The generic `telemetry_logs` table remains generic. It stores the stable event
ID, device, topic, event time, raw JSON payload, generic sensor values, status,
and ingestion/persistence timestamps. It does not contain vaccine-domain
columns.

The flattened `vaccine_temperature_events` table stores vaccine-specific
values: Pod, vaccine profile, scenario, temperature, safe range, uncertainty,
status, provenance, and lifecycle timestamps. Its `event_id` is both its
primary key and a foreign key to the generic raw event.

The canonical clean schema is:

```text
database/bootstrap/001_core.sql
```

Legacy data upgrades belong under `database/migrations/`. The clean bootstrap
does not contain experimental create-then-alter sequences.

## Reset safety

Reset deletes and recreates the application tables and indexes. It requires an
explicit flag, a development/demo/test environment, and a local PostgreSQL
host. It prints the target host and database and refuses production or remote
hosts.

```bash
APP_ENV=demo make reset-demo RESET_CONFIRM=YES
```

Without both the environment guard and explicit confirmation, the command
exits before connecting to PostgreSQL.

## Verification

Run persistence verification before opening the dashboard:

```bash
make verify
```

The checks show the latest event ID, device, Pod, vaccine, scenario,
temperature, status, event time, received time, ingestion latency, event age,
total count, and first/latest timestamps. The underlying SQL is in
`database/verification/latest_events.sql`.

## Tests

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
make test
node --test web/scripts/vaccine-data.test.js
```

The Python tests cover timestamp correctness, scenario invariants, atomic
dual-write success and rollback, duplicate idempotency, dashboard read mapping,
canonical schema structure, and reset guards.

## Troubleshooting

- **PostgreSQL unavailable:** run `pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT"`, then `brew services start postgresql@16`.
- **Mosquitto unavailable:** run `brew services start mosquitto` and verify port 1883.
- **Listener rejects an event:** inspect the structured `event_rejected` log; the listener recalculates uncertainty fields instead of trusting the sender.
- **No new rows:** confirm the listener uses `--write-db`, then run `make verify` before debugging the browser.
- **Old rows appear:** reset the demo database before an isolated scenario run.
- **Dashboard unavailable:** start `services/dashboard_bridge.py` and serve the `web/` directory separately.
- **Timestamps look historical:** inspect `event_time`, not `source_time`; the latter intentionally preserves the CSV reading time.

## Deferred work

ML-compatible export, training-schema contracts, retraining, versioned model
artifacts, deployed inference, and dashboard confidence display are the next
phase after the event/database/dashboard chain is stable and reproducible.
