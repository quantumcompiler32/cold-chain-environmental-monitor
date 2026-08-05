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

The maintained architecture, field definitions, setup/runbook, troubleshooting,
demo script, E2E contract, and presentation checklist are also available in
[`docs/`](docs/).

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
- The generator creates one `run_id` per invocation; every event in that run
  carries the same optional correlation value.
- The listener stamps `received_at` when it ingests the MQTT message.
- The persistence transaction stamps `stored_at` and writes both tables.
- The subscriber is the normal database write owner. Generator `--write-db`
  is an explicit direct mode and does not publish the same event to MQTT.
- The dashboard never connects directly to PostgreSQL and never writes data.
- The live dashboard and raw event page receive committed events through a
  PostgreSQL `LISTEN/NOTIFY` channel exposed as Server-Sent Events (SSE).
- A demo reset publishes a reset notification so open dashboard pages clear
  their in-memory analytics before the next isolated scenario.

## Where to find everything

Use this short map instead of searching the whole project:

| Need | Location |
| --- | --- |
| Install, start, stop, and restart | `README.md` and `docs/setup-and-runbook.md` |
| Architecture and event flow | `docs/architecture-and-pipeline.md` |
| Database ownership and queries | `docs/database-access.md` and `database/` |
| Event fields and status meanings | `docs/data-dictionary.md` |
| Verification commands and evidence | `docs/final-verification-report.md` and `docs/end-to-end-verification.md` |
| Troubleshooting | `docs/troubleshooting.md` |
| Executable services | `services/` |
| Verification/reset commands | `scripts/` |
| Automated tests | `tests/` |
| Browser dashboard | `web/` |

The only intentionally local-only folder is `.venv/`, the Python environment.
`models/`, `test-reports/`, and Python cache folders are generated on demand
and are not part of the source tree; they may reappear after training, E2E
verification, or test runs.

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

## Database setup

The application expects a local PostgreSQL database named `iotdb`. Create the
database and apply the canonical schema once:

```bash
createdb iotdb
psql -d iotdb -f database/bootstrap/001_core.sql
```

If the database or role already exists, skip `createdb`. Set the `POSTGRES_*`
variables above when the local role is not the current macOS user. The
bootstrap schema creates `telemetry_logs`, `vaccine_temperature_events`,
required indexes, and the `dashboard_events` notification channel. Migrations
under `database/migrations/` are only for an existing legacy database.

## Required startup order

Run each long-running command in its own terminal. This order is part of the
reproducible contract and identifies who owns each responsibility.

1. Check infrastructure and schema readiness:

   ```bash
   pg_isready -h "${POSTGRES_HOST:-localhost}" -p "${POSTGRES_PORT:-5432}"
   nc -z "${MQTT_BROKER:-localhost}" "${MQTT_PORT:-1883}"
   python3 scripts/verify_database.py
   ```

   If either service is stopped, run `make start-infrastructure` and repeat
   the checks.

2. Start the listener/database writer (Terminal 1):

   ```bash
   make start-listener LISTENER_OUTPUT_MODE=verbose
   ```

   `services.temperature_subscriber` owns the normal MQTT-to-PostgreSQL write
   transaction and writes both projections atomically.

3. Start the read-only dashboard adapter (Terminal 2):

   ```bash
   make start-dashboard
   ```

   Confirm it with `curl http://127.0.0.1:8787/ready`.

4. Start the static dashboard server (Terminal 3):

   ```bash
   python3 -m http.server 8766 --bind 127.0.0.1 --directory web
   ```

5. Start the optional ML service (Terminal 4) only when the Inference tab is
   being demonstrated:

   ```bash
   make start-ml-service
   ```

6. Open <http://127.0.0.1:8766/pages/domain-vaccine.html>. Start the event
   generator last, from another terminal:

   ```bash
   make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=9 INTERVAL_MS=100 SEED=104
   ```

   To demonstrate all supported Pod-grid states and fill Pods 1–20, use:

   ```bash
   make demo-all COUNT=30 INTERVAL_MS=200 OUTPUT_MODE=summary
   ```

7. Verify the same latest events in PostgreSQL and through the dashboard API:

   ```bash
   make verify-fast
   make verify
   curl http://127.0.0.1:8787/api/verification/latest-events
   curl 'http://127.0.0.1:8787/api/events?limit=10'
   ```

   The `event_id`, `run_id`, `sensor_name`, and `event_time` returned by the
   latest-events query must match the events shown at
   <http://127.0.0.1:8766/pages/domain-vaccine-raw.html>. The API is a
   read-only view of PostgreSQL, not a second event store.

Use `COUNT=10` for a faster run.

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

Open <http://127.0.0.1:8766/index.html> for the domain index or
<http://127.0.0.1:8766/pages/domain-vaccine-raw.html> for the live raw event
stream. The API remains on port 8787; page assets remain on port 8766.

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
--run-id ID
--write-db
--output-mode none|summary|verbose
```

Summary mode is the default. It reports requested, generated, published, and
failed counts; per-scenario counts; a separate phase breakdown for `mixed`;
first and last event times; elapsed seconds; and events per second. `verbose`
prints each event. `none` suppresses normal per-event output for large runs.

## Database design

The generic `telemetry_logs` table remains generic. It stores the stable
`event_id`, optional `run_id`, device, topic, event time, raw JSON payload,
generic sensor values, status, and ingestion/persistence timestamps. It does
not contain vaccine-domain columns.

The flattened `vaccine_temperature_events` table stores vaccine-specific
values: Pod, vaccine profile, scenario, temperature, safe range, uncertainty,
status, lifecycle timestamps, and optional `run_id`. Its `event_id` is both its
primary key and a foreign key to the generic raw event. These are two
intentional projections of one event, not two independent write paths; the
subscriber verifies that both rows exist before commit and notification.

The complete read/write ledger is in
[`docs/database-access.md`](docs/database-access.md).

The canonical clean schema is:

```text
database/bootstrap/001_core.sql
```

Legacy data upgrades belong under `database/migrations/`. The clean bootstrap
does not contain experimental create-then-alter sequences.

## Reset the dashboard view

This clears the open dashboard analytics view without deleting stored
PostgreSQL events. Historical filters can still load the retained data.

```bash
APP_ENV=demo make reset-dashboard
```

## Stop and restart

Stop the generator first, then stop the static server, bridge, and listener
with Ctrl-C in their terminals. Finally stop PostgreSQL and Mosquitto when
they are no longer needed:

```bash
make stop-demo
```

Restart by running `make start-infrastructure`, repeating the readiness checks,
and following the startup order above. Use `APP_ENV=demo RESET_CONFIRM=YES
make reset-demo` only when a clean demo database is required; it deletes the
application tables and is intentionally guarded.

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

Run the fast parity/readiness probe first:

```bash
python3 scripts/verify_database.py
```

It uses read-only transactions and returns one structured JSON object with
schema readiness, row counts, projection parity, latest `event_id`/`run_id`,
and elapsed milliseconds. It exits nonzero when PostgreSQL is unavailable or
the two projections are not in parity.

Run persistence verification before opening the dashboard:

```bash
python3 scripts/verify_persistence.py
```

The checks show the latest event ID, device, Pod, vaccine, scenario,
temperature, status, event time, received time, ingestion latency, event age,
total count, and first/latest timestamps. The underlying SQL is in
`database/verification/latest_events.sql`.

## API health and 404 diagnostics

The dashboard bridge serves API routes on `127.0.0.1:8787`; the website server
serves pages on `127.0.0.1:8766`. Use these checks:

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/ready
curl http://127.0.0.1:8787/api
```

`/health` is a process check. `/ready` proves that PostgreSQL and both
canonical tables are reachable. A page request sent to port `8787` returns a
structured 404 explaining that it belongs on port `8766`.

## Tests

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test web/scripts/vaccine-data.test.js
```

For the optional local PostgreSQL integration check, set
`RUN_DB_INTEGRATION=1`; it is skipped by default when no disposable database
is configured.

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
