# Cold-chain terminal runbook

This copy-paste runbook is written for macOS with Homebrew. On Linux, replace
the two Homebrew service commands with your distribution's PostgreSQL and
Mosquitto service commands, then continue with the same application commands.

## One-time setup

```bash
cd "$(git rev-parse --show-toplevel)"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
brew services start postgresql@16
brew services start mosquitto
```

## Dashboard reset command — keeps stored data

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
APP_ENV=demo make reset-dashboard
```

## Clear the demo database

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
APP_ENV=demo RESET_CONFIRM=YES make reset-demo
```

## Train the saved ML model

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
make train-models
```

## Terminal 1 — listener

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_subscriber --write-db --output-mode verbose
```

## Terminal 2 — dashboard bridge

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.dashboard_bridge
```

## Terminal 3 — dashboard website

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend
```

## Terminal 4 — ML inference service

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m ai_worker.ml_service
```

## Check dashboard bridge

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/ready
curl http://127.0.0.1:8787/api
```

## Check ML service

```bash
curl http://127.0.0.1:5000/health
```

## Open the dashboard

```text
http://127.0.0.1:8766/pages/domain-vaccine.html
```

## Generate live normal events

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario normal --count 30 --interval-ms 100 --seed 42 --output-mode summary
```

## Generate live outlier events

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario outlier --count 30 --interval-ms 100 --output-mode summary
```

## Generate live warning events

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario warning --count 30 --interval-ms 100 --output-mode summary
```

## Generate live recovery events

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario recovery --count 30 --interval-ms 100 --output-mode summary
```

## Generate a mixed event sequence

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario mixed --count 30 --interval-ms 100 --output-mode summary
```

## Generate events for multiple Pods

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 -m backend.temperature_event_generator --sensor Pod1 Pod2 Pod3 --scenario normal --count 30 --interval-ms 100 --output-mode summary
```

## Generate all demo states

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
make demo-all COUNT=30 INTERVAL_MS=200 OUTPUT_MODE=summary
```

## Verify persisted events

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
python3 db/verify_persistence.py
```

For a fast readiness and raw/domain parity check:

```bash
python3 db/verify_database.py
```

## Run tests

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv/bin/activate
make test
node --test frontend/tests/*.test.js
```
