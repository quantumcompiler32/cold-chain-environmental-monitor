# Setup and runbook

This is the reproducible local setup for the synthetic demo. It assumes macOS,
Homebrew PostgreSQL 16, Mosquitto, Python 3.12+, and Node.js.

## One-time setup

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
brew services start postgresql@16
brew services start mosquitto
```

Train the optional advisory model bundle once:

```bash
make train-models
```

## Run the full demo

Start each long-running service in its own terminal:

```bash
# Terminal 1
make start-listener LISTENER_OUTPUT_MODE=verbose

# Terminal 2
make start-dashboard

# Terminal 3
python3 -m http.server 8766 --bind 127.0.0.1 --directory web

# Terminal 4, optional ML tab
make start-ml-service
```

Open `http://127.0.0.1:8766/pages/domain-vaccine.html`.

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
node --test web/scripts/*.test.js phase1-stitch-ui/*.test.js
```
