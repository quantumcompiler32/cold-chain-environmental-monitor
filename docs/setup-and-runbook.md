# Setup and runbook

This is the reproducible local setup for the synthetic demo. It assumes macOS,
Homebrew PostgreSQL 16, Mosquitto, Python 3.12+, and Node.js.

## One-time setup

```bash
cd "$(git rev-parse --show-toplevel)"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
brew services start postgresql@16
brew services start mosquitto
```

Create the application database and canonical tables once:

```bash
createdb iotdb
psql -d iotdb -f db/bootstrap/001_core.sql
```

Before every run, check `pg_isready`, MQTT port 1883, and
`python3 db/verify_database.py`.

Train the optional advisory model bundle once:

```bash
make train-models
```

## Run the full demo

Start each long-running service in its own terminal, in this order:

```bash
# Terminal 1
make start-listener LISTENER_OUTPUT_MODE=verbose

# Terminal 2: read-only PostgreSQL dashboard adapter
make start-dashboard

# Terminal 3: static dashboard assets
python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend

# Terminal 4, optional ML tab
make start-ml-service
```

Open `http://127.0.0.1:8766/pages/domain-vaccine.html`, then start the event
generator last. Verify the same event IDs through PostgreSQL and the raw page:

```bash
make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=9 INTERVAL_MS=100 SEED=104
make verify-fast
make verify
curl http://127.0.0.1:8787/api/verification/latest-events
```

For a reproducible local replay with July timestamps, add an explicit start
time to the generator command. Every event timestamp, receipt timestamp, and
storage timestamp will use that simulated clock:

```bash
make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=9 INTERVAL_MS=100 SEED=104 START_TIME=2026-07-15T09:00:00-07:00
```

The bridge must report those same event IDs at
`http://127.0.0.1:8766/pages/domain-vaccine-raw.html`.

Generate a complete status demo from another terminal:

```bash
make demo-all COUNT=30 INTERVAL_MS=200 OUTPUT_MODE=summary
```

For a single deterministic scenario:

```bash
make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=9 INTERVAL_MS=100 SEED=104
```

## Reset and verify

To clear only the in-memory dashboard view while retaining database rows:

```bash
APP_ENV=demo make reset-dashboard
```

To recreate the local/demo application tables, use the explicit reset guard:

```bash
APP_ENV=demo RESET_CONFIRM=YES make reset-demo
```

Before presenting the dashboard, run the read-only persistence check:

```bash
make verify
```

## Tests

The single automated pipeline verification command is:

```bash
make e2e
```

It starts a temporary listener and bridge, runs the deterministic scenario
manifest, correlates each case by a unique `batch_id`, reads events through the
bridge API, and writes:

```text
test-reports/e2e-latest.json   # machine-readable
test-reports/e2e-latest.md     # human-readable
```

The command does not delete application rows. It requires local PostgreSQL,
Mosquitto, the application schema, and Python dependencies to be available.

Run independent checks separately when infrastructure is unavailable:

```bash
make test
node --test frontend/tests/*.test.js
```

Stop with Ctrl-C in reverse startup order (generator, web server, bridge,
listener), then run `make stop-demo` if PostgreSQL and Mosquitto should also
stop.
