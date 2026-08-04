# Cold-chain demo terminal runbook

This is the direct command guide, with one Make shortcut for the combined demo.

Project folder:

```text
/Users/mokshjoshi/Documents/Internship/sensordashboard
```

## One-command full status demo

After the listener, dashboard backend, and dashboard website are running, use
this from the project folder. It fills Pod1–Pod20 and leaves the grid showing
normal, warning, critical, offline, empty, and energy-waste states:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
make demo-all COUNT=30 INTERVAL_MS=200 OUTPUT_MODE=summary
```

Use `COUNT=10` for a faster demo. The command runs all generator cases in one
terminal; it does not require separate generator terminals.

The five scenarios are:

- `normal`: readings stay in the safe range.
- `warning`: readings stay in range while sensor uncertainty crosses a boundary.
- `recovery`: readings start warm and move back toward the target.
- `mixed`: one run split into normal, cooling failure, and recovery phases.
- `outlier`: every reading is outside the safe range, alternating cold and warm.

## Run the demo

### Setup terminal

Run this once:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
brew services start postgresql@16
brew services start mosquitto
APP_ENV=demo .venv/bin/python scripts/reset_demo.py --confirm-reset
```

### Train the model bundle

Run this once after installing dependencies, or again when the source CSV or
training behavior changes:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
make train-models
```

The command saves local model artifacts under `models/`. It does not connect to
PostgreSQL or modify dashboard events. The default label uses the Pfizer
ultralow profile; pass `VACCINE=moderna` to train against the Moderna range.

### Terminal 1: listener

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_subscriber --write-db --output-mode verbose
```

This receives MQTT events and writes both PostgreSQL tables.

### Terminal 2: dashboard backend

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.dashboard_bridge
```

### Terminal 3: dashboard website

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard/web
python3 -m http.server 8765 --bind 127.0.0.1
```

Open these pages:

```text
http://127.0.0.1:8765/index.html
http://127.0.0.1:8765/pages/domain-vaccine-raw.html
```

### Terminal 4: ML inference service

Start this after training the model bundle:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.ml_service
```

Check readiness:

```bash
curl http://127.0.0.1:5000/health
```

Open the Phase 1 local UI at `/phase1-stitch-ui/#interpretation`. Fill in the
Pod, temperature, vaccine, and scenario fields, then choose `Predict event`.
The form sends one event plus recent dashboard context and displays the
logistic result first. The service only returns analysis; it does not persist
the submitted event.

The raw page updates as soon as an event is stored. It does not wait for a
five-second poll.

### Terminal 5: run a scenario

Normal:

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

Recovery:

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

Warning:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_event_generator \
  --sensor Pod1 \
  --vaccine pfizer_ultralow \
  --scenario warning \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode verbose
```

Warning stays inside the stored range, but the sensor uncertainty interval
crosses the warm boundary, producing a warning rather than a critical event.

Mixed:

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

Outlier:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m services.temperature_event_generator \
  --sensor Pod1 \
  --vaccine pfizer_ultralow \
  --scenario outlier \
  --count 30 \
  --interval-ms 100 \
  --output-mode verbose
```

Outlier does not need a seed. Every event is deliberately too cold or too warm
for the selected vaccine range.

For a mixed run, the terminal and dashboard show:

```text
scenario: mixed
phase: normal

scenario: mixed
phase: cooling_failure

scenario: mixed
phase: recovery
```

The analytics chart shows separate Normal, Cooling failure, and Recovery bars.
The raw page also has an ALL PHASES filter.

## Reset before another scenario

Stop the listener with Control-C, then run:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
APP_ENV=demo python3 scripts/reset_demo.py --confirm-reset
```

Then start the listener again.

The reset command:

- only works in a local demo/development environment;
- prints the target host and database;
- recreates the tables and indexes;
- clears the open dashboard and raw-event pages.

## Check persistence

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 scripts/verify_persistence.py
```

This shows the newest events, event IDs, scenarios, phases, timestamps,
ingestion latency, event age, total count, and first/latest timestamps.

## Useful API commands

```bash
curl http://127.0.0.1:8787/health
curl 'http://127.0.0.1:8787/api/analytics?scenario=mixed'
curl 'http://127.0.0.1:8787/api/events?scenario=mixed'
curl 'http://127.0.0.1:8787/api/verification/latest-events'
curl -o vaccine_events.csv 'http://127.0.0.1:8787/api/events/export.csv'
```

The ML service uses a separate port and endpoint:

```text
GET  http://127.0.0.1:5000/health
POST http://127.0.0.1:5000/api/predict
```

To watch the live event stream directly:

```bash
curl -N http://127.0.0.1:8787/api/live/stream
```

The stream sends snapshot when it connects, event when a new event is stored,
and reset after the demo reset command runs.

The analytics API returns both top-level scenario counts and phase counts:

```text
scenario_counts: mixed
phase_counts: normal, cooling_failure, recovery
```

## Optional generator commands

Run these from the project folder after activating the environment:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
```

### Run multiple Pods together

Use one generator process and list the Pods after `--sensor`. The count is per
Pod, so this publishes 30 readings for each Pod while keeping the same interval
between rounds:

```bash
python3 -m services.temperature_event_generator \
  --sensor Pod1 Pod2 Pod3 \
  --vaccine pfizer_ultralow \
  --scenario mixed \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode summary
```

You can also write the list as `--sensor Pod1,Pod2,Pod3`. With Make:

```bash
make run-scenario SENSORS="Pod1 Pod2 Pod3" SCENARIO=mixed COUNT=30 INTERVAL_MS=100
```

Summary mode avoids printing every event:

```bash
python3 -m services.temperature_event_generator \
  --sensor Pod2 \
  --vaccine pfizer_ultralow \
  --scenario mixed \
  --count 300 \
  --interval-ms 20 \
  --seed 42 \
  --output-mode summary
```

The summary includes requested, generated, published, failed, per-scenario,
per-phase, first/last timestamps, elapsed time, and events per second.

Silent mode:

```bash
python3 -m services.temperature_event_generator \
  --scenario normal \
  --count 300 \
  --seed 42 \
  --output-mode none
```

Empty pod with cooling enabled:

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

Offline pod:

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

Moderna with a custom range:

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

## PostgreSQL inspection

```bash
psql -U mokshjoshi -d iotdb
```

```sql
\dt
\d telemetry_logs
\d vaccine_temperature_events

SELECT COUNT(*) AS raw_event_count FROM telemetry_logs;
SELECT COUNT(*) AS vaccine_event_count FROM vaccine_temperature_events;

SELECT
    raw.event_id,
    raw.event_time,
    raw.received_at,
    raw.stored_at,
    vaccine.sensor_name AS pod,
    vaccine.vaccine_type,
    vaccine.scenario,
    vaccine.scenario_phase,
    vaccine.temperature_c,
    vaccine.operational_status
FROM telemetry_logs AS raw
JOIN vaccine_temperature_events AS vaccine USING (event_id)
ORDER BY raw.event_time DESC, raw.event_id DESC
LIMIT 10;

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
    stored_at
FROM vaccine_temperature_events
ORDER BY event_time DESC, event_id DESC
LIMIT 10;

\q
```

The first two queries show that both tables received rows. The join shows that
the same `event_id` connects the generic raw event to the vaccine-specific row.

## Tests

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test web/scripts/vaccine-data.test.js
python3 -m py_compile services/*.py scripts/*.py
node --check web/scripts/vaccine.js
node --check web/scripts/vaccine-data.js
node --check web/scripts/vaccine-bridge.js
node --check web/scripts/vaccine-raw.js
```

## Stop the demo

Press Control-C in the listener, backend, frontend, and generator terminals.

Then stop the local services if needed:

```bash
brew services stop mosquitto
brew services stop postgresql@16
```

## Timestamp fields

```text
event_time   = when the generator creates the event
received_at  = when the listener receives the event
stored_at    = when PostgreSQL stores the event
```

All three are current UTC timestamps. The CSV only provides temperature
values. Its historical date and time are not stored or used for freshness.
