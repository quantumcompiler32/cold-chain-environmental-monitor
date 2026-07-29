# Cold-chain demo terminal runbook

This file is the copy-paste command guide for the current repository layout.
It uses the three current user-facing scenarios: `normal`, `recovery`, and
`mixed`.

The project directory is:

```bash
/Users/mokshjoshi/Documents/Internship/sensordashboard
```

## 1. One-time setup

Run this once, or whenever the virtual environment does not exist.

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -r requirements.txt
```

Start PostgreSQL and Mosquitto:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make start-infrastructure
```

Reset the local demo database. This is destructive and must be explicitly
confirmed:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

APP_ENV=demo make reset-demo RESET_CONFIRM=YES
```

Do not run the reset command against production or a remote database. The
reset command refuses non-local hosts and non-demo/development environments.

## 2. Terminal 1: start the database listener

Open a new terminal and leave this process running:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make start-listener
```

Equivalent command:

```bash
python3 -m services.temperature_subscriber --write-db
```

The listener receives MQTT events, validates them, and writes both
`telemetry_logs` and `vaccine_temperature_events` in one PostgreSQL
transaction.

## 3. Terminal 2: start the dashboard backend

Open another terminal and leave this process running:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make start-dashboard
```

Equivalent command:

```bash
python3 -m services.dashboard_bridge
```

The dashboard backend is read-only. It reads PostgreSQL and exposes API routes
for the browser.

## 4. Terminal 3: start the frontend web server

Open another terminal and leave this process running:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard/web

python3 -m http.server 8765 --bind 127.0.0.1
```

Open the dashboard at:

```text
http://127.0.0.1:8765/index.html
```

## 5. Terminal 4: run the normal scenario

Use a new terminal for the generator:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make run-scenario \
  SCENARIO=normal \
  COUNT=30 \
  INTERVAL_MS=100 \
  SEED=42 \
  OUTPUT_MODE=summary
```

Verify persistence after the generator finishes:

```bash
make verify
```

## 6. Run the recovery scenario in isolation

First stop the listener with `Control-C`. Then reset the database:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

APP_ENV=demo make reset-demo RESET_CONFIRM=YES
make start-listener
```

In another terminal, run recovery:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make run-scenario \
  SCENARIO=recovery \
  COUNT=30 \
  INTERVAL_MS=100 \
  SEED=42 \
  OUTPUT_MODE=summary

make verify
```

Expected behavior: temperatures begin outside the safe range and move back
toward the vaccine target.

## 7. Run the mixed scenario in isolation

Stop the listener with `Control-C`, reset, and restart it:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

APP_ENV=demo make reset-demo RESET_CONFIRM=YES
make start-listener
```

In another terminal, run mixed:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make run-scenario \
  SCENARIO=mixed \
  COUNT=30 \
  INTERVAL_MS=100 \
  SEED=42 \
  OUTPUT_MODE=summary

make verify
```

Expected phases:

```text
normal -> cooling_failure -> recovery
```

## 8. Direct generator commands

Normal events with the current default Pfizer profile:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

python3 -m services.temperature_event_generator \
  --sensor Pod1 \
  --vaccine pfizer_ultralow \
  --scenario normal \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode summary
```

Moderna with a custom safe range:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

python3 -m services.temperature_event_generator \
  --sensor Pod1 \
  --vaccine moderna \
  --min-temp -50 \
  --max-temp -15 \
  --scenario recovery \
  --count 300 \
  --interval-ms 400 \
  --seed 42 \
  --output-mode summary
```

The generator output modes are:

```text
none     no normal console output
summary  one final run summary; this is the default
verbose  print every generated event
```

For large runs, use `summary` or `none` instead of `verbose`.

## 9. Verify the database before opening the dashboard

Read-only verification script:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make verify
```

The output includes:

```text
event ID
Pod/device
vaccine
scenario
temperature
status
event_time
received_at
ingestion latency
event age
total count
first event time
latest event time
```

## 10. Inspect PostgreSQL manually

Open PostgreSQL:

```bash
psql -U mokshjoshi -d iotdb
```

Run these SQL commands inside `psql`:

```sql
\dt

\d telemetry_logs
\d vaccine_temperature_events

SELECT COUNT(*) FROM telemetry_logs;

SELECT COUNT(*) FROM vaccine_temperature_events;

SELECT
    event_id,
    sensor_name AS pod,
    vaccine_type,
    scenario,
    temperature_c,
    status,
    event_time,
    received_at,
    stored_at
FROM vaccine_temperature_events
ORDER BY event_time DESC, event_id DESC
LIMIT 10;

SELECT
    COUNT(*) AS total_count,
    MIN(event_time) AS first_event_time,
    MAX(event_time) AS latest_event_time
FROM vaccine_temperature_events;
```

Exit PostgreSQL:

```sql
\q
```

The current application tables are `telemetry_logs` and
`vaccine_temperature_events`. The old `temperature_events` table is legacy
schema and should not be used for the new demo flow.

## 11. Test the dashboard API directly

Health check:

```bash
curl http://127.0.0.1:8787/health
```

Chronological events for the live dashboard:

```bash
curl http://127.0.0.1:8787/api/events
```

Newest events first for verification:

```bash
curl http://127.0.0.1:8787/api/verification/latest-events
```

CSV export of persisted events:

```bash
curl http://127.0.0.1:8787/api/events/export.csv
```

## 12. Run automated tests

Python tests:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

make test
```

Browser data-layer tests:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard

node --test web/scripts/vaccine-data.test.js
```

Python syntax check:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate

python3 -m py_compile services/*.py scripts/*.py
```

## 13. Stop the demo

Stop the listener, dashboard backend, and frontend with `Control-C` in their
terminals. Then stop the local infrastructure:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard

make stop-demo
```

## 14. Timestamp explanation for a meeting

```text
source_time  = optional historical CSV provenance
event_time   = current time when the generator creates a new event
received_at  = time when the MQTT listener receives the event
stored_at    = time when PostgreSQL persists the event
```

The CSV timestamp is not used for freshness or latest-event ordering. The
generator creates new current events. `--seed 42` makes the scenario/value
pattern reproducible, but timestamps still represent the actual current run.
