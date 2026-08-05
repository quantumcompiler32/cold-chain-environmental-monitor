# Vaccine cold-chain environmental monitor

This repository is a self-contained local demonstration of a vaccine
temperature pipeline:

```text
event generator -> Mosquitto MQTT -> backend subscriber -> PostgreSQL
                                             -> read-only dashboard bridge -> frontend
```

The verified baseline is deterministic monitoring and persistence. The
`ai_worker/` package is optional and advisory; it does not write PostgreSQL
rows or make vaccine-disposition decisions. The `edge/` folder contains
hardware reference material and an optional serial diagnostic tool.

## Required software

- macOS or Linux with Python 3.12+. These are the supported laptop platforms.
- PostgreSQL 16 or a compatible PostgreSQL installation.
- Mosquitto MQTT broker.
- Node.js 18+ for frontend tests.
- `make` for the command shortcuts.
- Optional: Homebrew on macOS, PlatformIO for future Arduino firmware, and
  `pyserial` for `edge/tools/serial_diagnostics.py`.

## Repository layout

| Folder | Responsibility |
|---|---|
| `frontend/` | HTML, JavaScript, CSS, frontend tests, and browser assets |
| `db/` | PostgreSQL schema, migrations, reset/verification scripts, SQL, and database tests |
| `backend/` | Event generator, MQTT subscriber/database writer, dashboard bridge, E2E verifier, and backend tests |
| `ai_worker/` | Optional model trainer, inference service, training CSV, model artifacts, and ML tests |
| `edge/` | Arduino/sensor reference images, serial diagnostic tool, and hardware notes |
| `docs/` | Architecture, runbook, verification report, presentation, dataset, and research material |

## Configuration

The application uses these environment variables. Defaults are suitable for
the local demo:

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `iotdb` | PostgreSQL database |
| `POSTGRES_USER` | current local user | PostgreSQL role |
| `POSTGRES_PASSWORD` | unset | Optional password |
| `MQTT_BROKER` | `localhost` | Mosquitto host |
| `MQTT_PORT` | `1883` | Mosquitto port |
| `APP_ENV` | `development` | Safety environment; reset requires `demo` or `test` |
| `ML_SERVICE_HOST` | `127.0.0.1` | Optional inference service host |
| `ML_SERVICE_PORT` | `5000` | Optional inference service port |
| `ML_MODEL_DIR` | `ai_worker/models` | Optional model bundle directory |

Do not commit passwords or private connection strings. Export variables in a
terminal or load the provided local template:

```bash
cp .env.example .env
set -a
source .env
set +a
```

`.env` is ignored by Git; `.env.example` contains placeholders only. On
Windows, use the equivalent environment-variable commands in a supported
macOS or Linux environment such as WSL.

## One-time installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The package installation requires internet access. The application tests do
not require PostgreSQL or Mosquitto; `make e2e` does.

Create the local database once. If the database or role already exists, skip
the command that creates it:

```bash
createdb iotdb
psql -d iotdb -f db/bootstrap/001_core.sql
```

Start the required infrastructure and confirm it is reachable. On macOS with
Homebrew:

```bash
brew services start postgresql@16
brew services start mosquitto
pg_isready -h "${POSTGRES_HOST:-localhost}" -p "${POSTGRES_PORT:-5432}" -d "${POSTGRES_DB:-iotdb}"
mosquitto_pub -h "${MQTT_BROKER:-localhost}" -t dashboard/health -m ready
```

If you are not using Homebrew, start PostgreSQL and Mosquitto with your
platform's service manager instead.

For example, on Linux the service commands are commonly:

```bash
sudo systemctl start postgresql
sudo systemctl start mosquitto
```

Service names vary by distribution. Continue with the same `pg_isready` and
`mosquitto_pub` checks after starting them.

## Correct startup order

Use one terminal per long-running process. Run each terminal from the project
root with the virtual environment active.

1. Check PostgreSQL and Mosquitto using the readiness commands above.
2. Start the MQTT listener and database writer:

   ```bash
   make start-listener LISTENER_OUTPUT_MODE=verbose
   ```

3. Start the read-only dashboard bridge:

   ```bash
   make start-dashboard
   ```

4. Start the static frontend server:

   ```bash
   python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend
   ```

5. Start the event generator last:

   ```bash
   make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=9 INTERVAL_MS=100 SEED=104
   ```

Open `http://127.0.0.1:8766/` or
`http://127.0.0.1:8766/pages/domain-vaccine.html`. The bridge API is at
`http://127.0.0.1:8787/`.

## Generate events

The generator reads the reproducible source-variation CSV in
`ai_worker/data/`, creates current UTC event timestamps, and publishes MQTT
messages. It does not import a historical CSV timestamp.

```bash
make run-scenario SENSORS=Pod1 SCENARIO=normal COUNT=30 INTERVAL_MS=100 SEED=42
make run-scenario SENSORS=Pod1 SCENARIO=warning COUNT=30 INTERVAL_MS=100 SEED=42
make run-scenario SENSORS=Pod1 SCENARIO=outlier COUNT=30 INTERVAL_MS=100
make run-scenario SENSORS=Pod1 SCENARIO=recovery COUNT=30 INTERVAL_MS=100
make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=30 INTERVAL_MS=100 SEED=42
make demo-all COUNT=10 INTERVAL_MS=200 OUTPUT_MODE=summary
```

The listener is the normal database writer. Direct generator database writes
are not part of the normal startup order; `--write-db` belongs to the listener.

## Database reset and verification

Reset is destructive and guarded. It is only for a local demo database:

```bash
APP_ENV=demo RESET_CONFIRM=YES make reset-demo
```

The reset recreates the application tables. The non-destructive verification
commands prove the current schema, latest events, and projection parity:

```bash
make verify-fast
make verify
psql -d iotdb -f db/verification/latest_events.sql
```

The latest-N query is read-only. It should show current `event_time`,
`received_at`, `stored_at`, batch IDs, and operational states after a generator
run.

## Optional AI worker

The AI worker is not required for the baseline dashboard. To train the
educational models and start the read-only inference service:

```bash
make train-models
make start-ml-service
```

The trainer reads `ai_worker/data/Test1_TempCO2O2.csv` and writes the bundle to
`ai_worker/models/`. These outputs are provided as project artifacts; retrain
only when intentionally changing the training input.

## Tests and end-to-end verification

Run the complete local test suite:

```bash
make test
```

Run the deterministic public-process scenario after PostgreSQL and Mosquitto
are running:

```bash
make e2e
```

The E2E verifier runs normal, warning, recovery, mixed, and outlier scenarios,
checks the HTTP bridge, reads the current run back from PostgreSQL, and writes
ignored evidence under `test-reports/`.

## Stop and restart

Stop the four application terminals with `Ctrl-C` in this order: generator,
frontend server, dashboard bridge, then listener. Stop infrastructure only if
you no longer need it:

```bash
make stop-demo
```

Restart by starting PostgreSQL and Mosquitto, running the listener, starting
the bridge, serving `frontend/`, and launching the generator last. Use
`make reset-dashboard` to clear only the bridge's in-memory view without
deleting PostgreSQL rows. Use `make reset-demo` only when a clean demo database
is explicitly required.

## Documentation

- [`docs/architecture-and-pipeline.md`](docs/architecture-and-pipeline.md) — component responsibilities and data flow.
- [`docs/database-access.md`](docs/database-access.md) — database read/write ownership and SQL boundaries.
- [`docs/terminal-runbook.md`](docs/terminal-runbook.md) — copy-paste process commands.
- [`docs/demo-script.md`](docs/demo-script.md) — demonstration sequence.
- [`docs/final-verification-report.md`](docs/final-verification-report.md) — acceptance evidence and risks.
- [`edge/README.md`](edge/README.md) — hardware and sensor notes.
