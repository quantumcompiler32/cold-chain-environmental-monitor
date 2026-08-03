# Vaccine cold-chain terminal runbook

All commands below assume the terminal is in the `vaccine` project root.

## Setup terminal

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
brew services start postgresql@16
brew services start mosquitto
APP_ENV=demo .venv/bin/python db/scripts/reset_demo.py --confirm-reset
```

## Terminal 1: listener/subscriber

```bash
source .venv/bin/activate
PYTHONPATH=backend .venv/bin/python -m services.temperature_subscriber --write-db --output-mode verbose
```

This receives MQTT events, validates them, and writes the generic raw event and
flattened vaccine event in one PostgreSQL transaction.

## Terminal 2: dashboard bridge

```bash
source .venv/bin/activate
PYTHONPATH=backend .venv/bin/python -m services.dashboard_bridge
```

The bridge is read-only from the browser's perspective and exposes the
persisted data to the frontend.

## Terminal 3: frontend

```bash
python3 -m http.server 8765 --directory frontend --bind 127.0.0.1
```

Open the analytics page at
<http://127.0.0.1:8765/pages/domain-vaccine.html> or the raw event page at
<http://127.0.0.1:8765/pages/domain-vaccine-raw.html>.

## Terminal 4: event generator

```bash
source .venv/bin/activate
PYTHONPATH=backend .venv/bin/python -m services.temperature_event_generator \
  --sensor Pod1 \
  --scenario mixed \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode summary
```

Scenarios:

- `normal` - readings remain in the selected vaccine profile range.
- `warning` - uncertainty crosses a boundary while the central reading remains in range.
- `recovery` - readings begin outside range and move toward the target.
- `mixed` - deterministic normal, cooling-failure, and recovery phases.
- `outlier` - readings remain outside the safe range.

## Verify persistence

```bash
.venv/bin/python db/scripts/verify_persistence.py
```

This proves that fresh rows reached PostgreSQL; it does not merely prove that
the listener or dashboard process is running.

## Reset between isolated demos

```bash
APP_ENV=demo .venv/bin/python db/scripts/reset_demo.py --confirm-reset
```

The command refuses production environments, remote hosts, and missing
confirmation. Start the listener and bridge again if they were stopped.

## Automated checks

```bash
make -C backend test
node --test frontend/scripts/vaccine-data.test.js
python3 -m py_compile backend/services/*.py db/scripts/*.py
```

## Optional experimental edge path

The Arduino material in `edge/` is not required for this runbook. It is an
untested standalone UNO R4 WiFi prototype. See `edge/README.md` for its
possible features, hardware images, limitations, and future integration work.
