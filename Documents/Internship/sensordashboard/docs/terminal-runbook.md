# Cold-chain demo terminal runbook

This is the copy-paste guide for the three current scenarios:

- `normal`: readings stay in the vaccine safe range.
- `recovery`: readings start warm and move back toward the target.
- `mixed`: one run with separate `normal`, `cooling_failure`, and `recovery` phases.

The commands below use the actual programs. No Make commands are required.

Project directory:

```text
/Users/mokshjoshi/Documents/Internship/sensordashboard
```

## Most useful commands: full normal demo

Run the first block once in a setup terminal:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
brew services start postgresql@16
brew services start mosquitto
APP_ENV=demo .venv/bin/python scripts/reset_demo.py --confirm-reset
```

Open Terminal 1 and leave the listener running:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_subscriber --write-db --output-mode verbose
```

Open Terminal 2 and leave the dashboard backend running:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.dashboard_bridge
```

Open Terminal 3 and leave the frontend running:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard/web
python3 -m http.server 8765 --bind 127.0.0.1
```

Open the dashboard at:

```text
http://127.0.0.1:8765/index.html
http://127.0.0.1:8765/pages/domain-vaccine-raw.html
```

Open Terminal 4 and publish the normal scenario:

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
  --output-mode verbose
```

Verify the rows after the generator finishes:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 scripts/verify_persistence.py
```

The listener prints each received event, its event time, receipt time,
storage result, scenario, phase when present, pod status, and alert. The
generator's default output is `summary`, which reports the requested scenario
separately from the optional mixed-run phase breakdown and avoids printing
every event in large runs.

The analytics and raw-event pages receive new committed rows immediately over
the live event stream. They do not wait for a five-second browser poll. When
the reset command runs, already-open pages receive a reset signal and clear
their in-memory analytics before the next scenario begins.

## Run recovery by itself

Stop the listener with `Control-C`, reset the demo database, and start the
listener again:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
APP_ENV=demo .venv/bin/python scripts/reset_demo.py --confirm-reset
python3 -m services.temperature_subscriber --write-db --output-mode verbose
```

In another terminal, publish recovery:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_event_generator \
  --sensor Pod1 \
  --vaccine pfizer_ultralow \
  --scenario recovery \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode verbose
```

Expected behavior: the first reading is outside the safe range and later
readings move toward the target.

## Run mixed by itself

Stop the listener, reset the demo database, and start the listener again:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
APP_ENV=demo .venv/bin/python scripts/reset_demo.py --confirm-reset
python3 -m services.temperature_subscriber --write-db --output-mode verbose
```

In another terminal, publish mixed:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_event_generator \
  --sensor Pod1 \
  --vaccine pfizer_ultralow \
  --scenario mixed \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode verbose
```

The displayed fields stay unambiguous:

```text
scenario: mixed
phase: normal
scenario: mixed
phase: cooling_failure
scenario: mixed
phase: recovery
```

`mixed` is the scenario. The phase describes the current part of that mixed
run; it is not combined into a value such as `mixed/recovery`.

## Useful optional commands

Use `summary` for a compact generator result. It reports requested, generated,
published, failed, per-phase counts, first/last event times, elapsed time, and
events per second:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_event_generator \
  --sensor Pod2 \
  --vaccine pfizer_ultralow \
  --scenario mixed \
  --count 300 \
  --interval-ms 20 \
  --seed 42 \
  --output-mode summary
```

Use `none` when the generator should be silent:

```bash
python3 -m services.temperature_event_generator --scenario normal --count 300 --seed 42 --output-mode none
```

Run an empty pod with cooling enabled to demonstrate energy waste:

```bash
python3 -m services.temperature_event_generator \
  --sensor Pod3 \
  --vaccine pfizer_ultralow \
  --scenario normal \
  --occupancy-state empty \
  --cooling-enabled \
  --count 10 \
  --interval-ms 100 \
  --seed 7 \
  --output-mode verbose
```

Run an offline pod. Offline is intentionally different from empty:

```bash
python3 -m services.temperature_event_generator \
  --sensor Pod4 \
  --vaccine pfizer_ultralow \
  --scenario normal \
  --occupancy-state offline \
  --count 10 \
  --interval-ms 100 \
  --seed 8 \
  --output-mode verbose
```

Use Moderna only with an explicit safe range:

```bash
python3 -m services.temperature_event_generator \
  --sensor Pod5 \
  --vaccine moderna \
  --min-temp -50 \
  --max-temp -15 \
  --scenario recovery \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode summary
```

## Verification and PostgreSQL inspection

The reusable verification command shows the newest events, total count, first
event time, latest event time, ingestion latency, and event age:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 scripts/verify_persistence.py
```

Call the read-only dashboard API directly:

```bash
curl http://127.0.0.1:8787/health
curl 'http://127.0.0.1:8787/api/live'
curl 'http://127.0.0.1:8787/api/events?scenario=mixed&severity=critical'
curl 'http://127.0.0.1:8787/api/analytics?pod=Pod1&scenario=mixed'
curl 'http://127.0.0.1:8787/api/verification/latest-events'
curl -o vaccine_events.csv 'http://127.0.0.1:8787/api/events/export.csv?pod=Pod1'
```

Inspect PostgreSQL manually:

```bash
psql -U mokshjoshi -d iotdb
```

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
    scenario_phase,
    occupancy_state,
    batch_id,
    operational_status,
    severity,
    temperature_c,
    status,
    event_time,
    received_at,
    stored_at,
    EXTRACT(EPOCH FROM (received_at - event_time)) * 1000 AS ingestion_latency_ms,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - event_time)) AS event_age_seconds
FROM vaccine_temperature_events
ORDER BY event_time DESC, event_id DESC
LIMIT 10;

SELECT COUNT(*) AS total_count,
       MIN(event_time) AS first_event_time,
       MAX(event_time) AS latest_event_time
FROM vaccine_temperature_events;
\q
```

## Tests and troubleshooting

Run the automated checks:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test web/scripts/vaccine-data.test.js
python3 -m py_compile services/*.py scripts/*.py
node --check web/scripts/vaccine.js
node --check web/scripts/vaccine-data.js
node --check web/scripts/vaccine-bridge.js
```

Common fixes:

- If PostgreSQL or Mosquitto is unavailable, run `brew services list` and start
  the missing service with `brew services start postgresql@16` or
  `brew services start mosquitto`.
- If the listener reports missing tables, run the explicit reset command in the
  setup section and confirm `APP_ENV=demo` is set.
- If the dashboard says PostgreSQL is unavailable, check
  `curl http://127.0.0.1:8787/health` and read the dashboard backend terminal.
- If the dashboard is blank, confirm the frontend is serving the `web`
  directory and that the listener and generator terminals are still running.
- If an event is shown as a duplicate, its stable `event_id` was already
  processed. This is expected idempotent behavior.

## Stop the demo

Press `Control-C` in the listener, dashboard backend, frontend, and generator
terminals. Then stop local infrastructure if it is no longer needed:

```bash
brew services stop mosquitto
brew services stop postgresql@16
```

## Timestamp explanation

```text
event_time   = current UTC time when the generator creates the event
received_at  = current UTC time when the MQTT listener receives the event
stored_at    = current UTC time when PostgreSQL stores the event
```

The CSV contributes temperature readings used to shape the simulation. Its
historical date/time is not copied into generated events, database rows, CSV
exports, or the dashboard. A seed makes the generated IDs, source-row choice,
and scenario/value pattern reproducible; it does not freeze the timestamps.
