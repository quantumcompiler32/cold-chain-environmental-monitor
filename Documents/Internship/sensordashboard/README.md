# Vaccine cold-chain monitoring demo

This project is a local, synthetic vaccine cold-chain monitoring pipeline. It
simulates Pod temperature events, transports them through MQTT, validates and
persists them in PostgreSQL, and presents the persisted evidence through a
read-only dashboard adapter.

The dashboard now includes a small, educational ML inference path. Training is
an explicit one-time step; the standalone service only loads saved artifacts
and scores one event at a time. The service is read-only and does not change
PostgreSQL events or vaccine disposition.

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

- The CSV is guidance for source variation and event shape. It is not part of
  the live event timestamp contract.
- The generator creates a new stable `event_id` and current UTC `event_time`.
- The listener stamps `received_at` when it ingests the MQTT message.
- The persistence transaction stamps `stored_at` and writes both tables.
- The dashboard never connects directly to PostgreSQL and never writes data.
- The live dashboard and raw event page receive committed events through a
  PostgreSQL `LISTEN/NOTIFY` channel exposed as Server-Sent Events (SSE).
- A demo reset publishes a reset notification so open dashboard pages clear
  their in-memory analytics before the next isolated scenario.

## Timestamp fields

| Field | Meaning |
| --- | --- |
| `event_time` | Current UTC time when the simulated event is created |
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

Train the local model bundle once before starting the inference service:

```bash
make train-models
```

This reads the bundled Pod CSV, converts Fahrenheit readings to Celsius, uses
Pod temperature features only, and writes local artifacts under `models/`.
Generated artifacts are ignored by Git and can be recreated at any time.
Use `make train-models VACCINE=moderna` when the model label should use the
Moderna profile range instead.

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

Once the listener, dashboard bridge, and website are running, this single
command demos every Pod-grid status and fills Pods 1–20:

```bash
make demo-all COUNT=30 INTERVAL_MS=200 OUTPUT_MODE=summary
```

Use `COUNT=10` for a faster run.

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
brew services start postgresql@16
brew services start mosquitto
APP_ENV=demo python3 scripts/reset_demo.py --confirm-reset
python3 -m services.temperature_subscriber --write-db --output-mode verbose
python3 -m services.temperature_event_generator --scenario normal --count 30 --interval-ms 100 --seed 42 --output-mode summary
python3 scripts/verify_persistence.py
python3 -m services.dashboard_bridge
```

Start the ML inference service in another terminal:

```bash
python3 -m services.ml_service
```

It listens on `http://127.0.0.1:5000` by default. The Phase 1 Interpretation
tab submits one simple event to `POST /api/predict`; it may include recent
context automatically. `GET /health` reports whether the saved model bundle is
loaded.

To run several Pods from one terminal, list them after `--sensor`. The count
is per Pod, and one event is published for each selected Pod on every interval:

```bash
python3 -m services.temperature_event_generator \
  --sensor Pod1 Pod2 Pod3 \
  --scenario mixed \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode summary
```

Comma-separated Pods work too: `--sensor Pod1,Pod2,Pod3`.

Serve the browser in another terminal:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard/web
python3 -m http.server 8765 --bind 127.0.0.1
```

Open <http://127.0.0.1:8765/index.html> for analytics or
<http://127.0.0.1:8765/pages/domain-vaccine-raw.html> for the live raw event
stream.

The generator supports five current user-facing scenarios:

- `normal`: translated source variation stays inside the vaccine profile range.
- `warning`: stays inside the range while the ±0.5°C sensor uncertainty crosses the warm boundary.
- `recovery`: begins above the safe range and moves back toward the profile target.
- `mixed`: deterministic normal, cooling-failure, and recovery phases.
- `outlier`: every event is intentionally outside the safe range, alternating cold and warm readings.

The analytics chart splits a mixed run into `Normal`, `Cooling failure`, and
`Recovery` phase bars while preserving `mixed` as the stored top-level
scenario. The raw event page shows both fields and the complete persisted
event payload.

ML results are advisory `ML-assisted analysis`. Logistic regression is the
primary event result; linear regression and k-means provide secondary context.
Results identify their model version, validation measure, and data basis, and
return an explicit insufficient-data state when context is not available.

The public CLI controls are:

```text
--scenario normal|warning|recovery|mixed|outlier
--vaccine pfizer_ultralow|moderna
--count N
--interval-ms N
--seed N
--write-db
--output-mode none|summary|verbose
```

Summary mode is the default. It reports requested, generated, published, and
failed counts; per-scenario counts; a separate phase breakdown for `mixed`;
first and last event times; elapsed seconds; and events per second. `verbose`
prints each event. `none` suppresses normal per-event output for large runs.

## Database design

The generic `telemetry_logs` table remains generic. It stores the stable event
ID, device, topic, event time, raw JSON payload, generic sensor values, status,
and ingestion/persistence timestamps. It does not contain vaccine-domain
columns.

The flattened `vaccine_temperature_events` table stores vaccine-specific
values: Pod, vaccine profile, scenario, temperature, safe range, uncertainty,
status, and lifecycle timestamps. Its `event_id` is both its
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
APP_ENV=demo python3 scripts/reset_demo.py --confirm-reset
```

Without both the environment guard and explicit confirmation, the command
exits before connecting to PostgreSQL.

## Verification

Run persistence verification before opening the dashboard:

```bash
python3 scripts/verify_persistence.py
```

The checks show the latest event ID, device, Pod, vaccine, scenario,
temperature, status, event time, received time, ingestion latency, event age,
total count, and first/latest timestamps. The underlying SQL is in
`database/verification/latest_events.sql`.

## Tests

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test web/scripts/vaccine-data.test.js
```

The Python tests cover timestamp correctness, scenario invariants, atomic
dual-write success and rollback, duplicate idempotency, dashboard read mapping,
canonical schema structure, and reset guards.

## Troubleshooting

- **PostgreSQL unavailable:** run `pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT"`, then `brew services start postgresql@16`.
- **Mosquitto unavailable:** run `brew services start mosquitto` and verify port 1883.
- **Listener rejects an event:** inspect the structured `event_rejected` log; the listener recalculates uncertainty fields instead of trusting the sender.
- **No new rows:** confirm the listener uses `--write-db`, then run `python3 scripts/verify_persistence.py` before debugging the browser.
- **Old rows appear:** reset the demo database before an isolated scenario run.
- **Dashboard unavailable:** start `services/dashboard_bridge.py` and serve the `web/` directory separately.
- **Timestamps look historical:** inspect `event_time`; the CSV is only used to guide event shape and temperature variation.

## Deferred work

ML-compatible export, training-schema contracts, retraining, versioned model
artifacts, deployed inference, and dashboard confidence display are the next
phase after the event/database/dashboard chain is stable and reproducible.
