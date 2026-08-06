# Vaccine cold-chain environmental monitor

This repository is a self-contained local demonstration of a vaccine
temperature pipeline:

```text
event generator -> Mosquitto MQTT -> backend subscriber -> PostgreSQL
                                             -> read-only dashboard bridge -> frontend
```

The verified baseline is deterministic monitoring, persistence, and the
browser dashboard. The `ai_worker/` package is optional and advisory; it does
not write PostgreSQL rows or make vaccine-disposition decisions. The `edge/`
folder contains hardware and sensor reference material; physical Arduino
firmware and calibrated sensor collection remain planned work.

## Required software

- macOS or Linux with Python 3.12+. These are the supported laptop platforms.
- PostgreSQL 16 or a compatible PostgreSQL installation.
- Mosquitto MQTT broker.
- Node.js 18+ for frontend tests.
- `make` for the command shortcuts.
- Optional: Homebrew on macOS and PlatformIO for future Arduino firmware.

## Repository layout

| Folder | Responsibility |
|---|---|
| `frontend/` | HTML, JavaScript, CSS, frontend tests, and browser assets |
| `db/` | PostgreSQL schema, migrations, reset/verification scripts, SQL, and database tests |
| `backend/` | Event generator, MQTT subscriber/database writer, dashboard bridge, E2E verifier, and backend tests |
| `ai_worker/` | Optional model trainer, inference service, training CSV, model artifacts, and ML tests |
| `edge/` | Arduino/sensor reference images and hardware notes |
| `docs/` | Architecture, runbook, verification report, presentation, dataset, and research material |

The package intentionally contains only this project's dashboard and related
implementation files. The original sensor-dashboard archive and unrelated
intern files are not part of the handoff.

## Dashboard

The dashboard is a browser-only frontend served from `frontend/`. The main
entry points are:

- `frontend/index.html` — landing page.
- `frontend/pages/domain-vaccine.html` — primary vaccine-monitoring view.
- `frontend/pages/domain-vaccine-raw.html` — raw event records.
- `frontend/pages/domain-vaccine-inference.html` — advisory model output.
- `frontend/pages/domain-cooling.html`, `domain-energy.html`, `domain-air.html`, and `domain-fire.html` — additional domain views.
- `frontend/pages/audit-log.html` and `frontend/pages/settings.html` — audit and configuration views.

The frontend reads through `backend/dashboard_bridge.py` on port `8787` and
does not write directly to PostgreSQL or MQTT. Its static files are served on
port `8766`. The bridge provides read-only API and server-sent-event streams
for committed records. Frontend tests cover navigation, aggregation,
filtering, CSV export, timestamps, bridge behavior, and inference rendering.

## Complete project contents

- `frontend/` contains the dashboard HTML, JavaScript, CSS, browser assets,
  and frontend tests.
- `db/` contains PostgreSQL bootstrap schema, migrations, guarded reset and
  verification scripts, sample-data helpers, and database tests.
- `backend/` contains the deterministic event generator, MQTT subscriber and
  database writer, dashboard bridge, event contracts, domain rules, and
  backend tests.
- `ai_worker/` contains training and inference code, the canonical training
  CSV, eight Colab notebooks, four saved model artifacts, and ML tests. The
  downloaded notebooks are `Combined notebook.ipynb`, `ML questions Ultralow
  Vaccine Distribution Data.ipynb`, `algorithms.ipynb`,
  `byteSmart_Ultralow_ML_Questions.ipynb`, `Testing Inference.ipynb`,
  `Training.ipynb`, `iot_data_analysis.ipynb`, and `Kaggle.ipynb`.
- `edge/` contains the README and reference images for the Arduino UNO R4
  WiFi, UNO R4 Minima, DHT22, BMP280, and AHT20. No completed Arduino sketch
  is claimed as physical validation.
- `docs/datasets/` contains the downloaded `14888121` dataset archive;
  `ai_worker/data/Test1_TempCO2O2.csv` remains the canonical CSV consumed by
  the trainer and generator.
- `docs/research/` contains the ultralow-temperature research PDF, student
  research document, ML questions document, final clinical protocol report,
  resource index, and `research_urls.doc`.
- `docs/presentation/` contains the PowerPoint deck and exported Google Slides
  presentation.
- `docs/lessons/`, `docs/learning-records/`, and `docs/assets/` contain the
  project lessons, engineering notes, and lesson styling assets.
- `docs/RESOURCES.md` contains the short list of repository and technical
  source links.

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

   This starts the API/SSE server on port `8787` in the background and records
   its PID in `.runtime/dashboard_bridge.pid`. Its output is written to
   `.runtime/dashboard_bridge.log`.

4. Start the static frontend server:

   ```bash
   python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend
   ```

5. Start the event generator last:

   ```bash
   make run-scenario \
  SENSORS=ALL \
  SCENARIO=mixed \
  COUNT=10 \
  INTERVAL_MS=100 \
  SEED=274 \
   ```

Open `http://127.0.0.1:8766/` or
`http://127.0.0.1:8766/pages/domain-vaccine.html`. The bridge API is at
`http://127.0.0.1:8787/`.

To watch the forward-only Live stream in a separate terminal, while keeping
the bridge available for the dashboard, run:

```bash
make watch-dashboard
```

This verifies the recorded bridge PID and its `/ready` endpoint, then opens
`curl -v -N http://127.0.0.1:8787/api/live/stream`. It also tails
`.runtime/dashboard_bridge.log`, so the terminal shows HTTP headers, bridge API
requests, PostgreSQL read records, SSE events, and keep-alive frames. Press
`Ctrl-C` to stop only the watcher. It does not start the bridge or kill
processes by port number.

Keep-alive frames are expected when no new event has been committed. They mean
the SSE HTTP connection is still open; the next committed event is delivered
on that same connection.

## Generate events

The generator reads the reproducible source-variation CSV in
`ai_worker/data/`, creates current UTC event timestamps by default, and
publishes MQTT messages. It does not import a historical CSV timestamp.

For a local replay, pass an ISO-8601 `START_TIME`. The timezone offset is
optional; when omitted, the timestamp uses the computer's local timezone. Each
round advances by `INTERVAL_MS`; the event, receipt, and storage timestamps are
all derived from that simulated clock, so the dashboard can show a July run
while you execute it today. This is intended for local demos and tests:

```bash
make run-scenario \
  SENSORS=ALL \
  SCENARIO=mixed \
  COUNT=10 \
  INTERVAL_MS=100 \
  SEED=274
```

For exact cross-timezone reproduction, include an offset such as
`START_TIME=2026-07-15T09:00:00-07:00`; otherwise each machine interprets the
same clock text in its own local timezone.

```bash
make run-scenario SENSORS=Pod1 SCENARIO=normal COUNT=30 INTERVAL_MS=100 SEED=42
make run-scenario SENSORS=ALL SCENARIO=normal COUNT=30 INTERVAL_MS=100 SEED=42
make run-scenario SENSORS=Pod1 SCENARIO=warning COUNT=30 INTERVAL_MS=100 SEED=42
make run-scenario SENSORS=Pod1 SCENARIO=outlier COUNT=30 INTERVAL_MS=100
make run-scenario SENSORS=Pod1 SCENARIO=recovery COUNT=30 INTERVAL_MS=100
make run-scenario SENSORS=Pod1 SCENARIO=mixed COUNT=30 INTERVAL_MS=100 SEED=42
make run-scenario SENSORS=ALL SCENARIO=mixed COUNT=100 INTERVAL_MS=100 SEED=42
make demo-all COUNT=10 INTERVAL_MS=200 OUTPUT_MODE=summary
```

When `SCENARIO=mixed` runs across multiple Pods, the generator assigns a
deterministic role by Pod: Normal, Recovery, Normal, Warning, Critical, Empty,
then Energy waste, repeating as needed. It does not assign Offline in this
mode, so the Pod grid shows a useful variety while the same seed and replay
time remain reproducible.

The listener is the normal database writer. Direct generator database writes
are not part of the normal startup order; `--write-db` belongs to the listener.

## Database verification

This README intentionally contains no command that drops, truncates, deletes,
or recreates PostgreSQL data. Keep existing rows and use the read-only
verification commands below to inspect the current schema, latest events, and
projection parity:

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

Stop the generator and static frontend with `Ctrl-C`. Stop the separate SSE
watcher with `Ctrl-C`, then stop the dashboard bridge through its recorded PID:

```bash
make stop-dashboard
```

`make stop-dashboard` verifies that the PID belongs to
`backend.dashboard_bridge`, sends `SIGTERM`, removes the PID file, and reports
if the bridge is already stopped. It never scans or kills every process using
port `8787`. Stop the listener afterward. Stop infrastructure only if you no
longer need it:

```bash
make stop-demo
```

Restart by starting PostgreSQL and Mosquitto, running the listener, starting
the bridge, serving `frontend/`, and launching the generator last.

The dashboard Live view starts empty and listens only for events committed
after the view is opened. Use the time presets, date fields, and other filters
to query persisted history; clicking **Apply filters** refreshes the dashboard
from those selected PostgreSQL rows. No database reset is needed for normal
dashboard use.

## Documentation

- [`docs/architecture-and-pipeline.md`](docs/architecture-and-pipeline.md) — component responsibilities and data flow.
- [`docs/database-access.md`](docs/database-access.md) — database read/write ownership and SQL boundaries.
- [`docs/MD Files for Running/terminal-runbook.md`](docs/MD%20Files%20for%20Running/terminal-runbook.md) — copy-paste process commands.
- [`docs/research/project-resource-index.md`](docs/research/project-resource-index.md) — package map and Colab/Drive resource status.
- [`edge/README.md`](edge/README.md) — hardware and sensor notes.
