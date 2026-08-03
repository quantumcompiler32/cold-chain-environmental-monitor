# Vaccine cold-chain environmental monitor

This package contains the vaccine cold-chain project prepared for handoff. The
verified demonstration is a local synthetic pipeline:

```text
event generator -> Mosquitto MQTT -> subscriber -> PostgreSQL -> read-only bridge -> dashboard
```

The Arduino material is included separately as an explicitly experimental edge
prototype. It is not required for the verified demonstration.

## Package layout

- `frontend/` - vaccine dashboard HTML, JavaScript, CSS, and frontend tests.
- `db/` - schema, migrations, reset and verification SQL, database scripts, and database tests.
- `ai_worker/` - notebooks, model artifacts, ML scripts, ML datasets, and supporting AI documentation.
- `backend/` - MQTT event generator/subscriber, dashboard bridge, backend utilities, simulator data, requirements, and backend tests.
- `edge/` - untested Arduino UNO R4 WiFi firmware prototype, hardware images, and edge README.
- `docs/` - runbooks, final reports, presentations, research, and research URLs.

Excluded source material such as old prototypes, duplicate drafts, unrelated
SensorDashboard domains, original upload packages, and other interns' files is
kept outside this handoff package.

## Verified demonstration prerequisites

- macOS with Homebrew
- Python 3.12 or newer
- PostgreSQL 16
- Mosquitto
- Node.js for frontend tests

From this `vaccine` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
brew services start postgresql@16
brew services start mosquitto
```

Supported environment variables include `APP_ENV`, `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`MQTT_BROKER`, `MQTT_PORT`, and `MQTT_TOPIC`.

## Reset and recreate the database

The reset command is guarded. It requires a development/demo/test environment,
a local PostgreSQL host, and explicit confirmation.

```bash
APP_ENV=demo .venv/bin/python db/scripts/reset_demo.py --confirm-reset
```

The clean schema is `db/bootstrap/001_core.sql`. Additive upgrades belong under
`db/migrations/`. The verification query is
`db/verification/latest_events.sql`.

## Start the verified pipeline

Run each long-running process in its own terminal. Activate the virtual
environment in each terminal and run these commands from the `vaccine`
directory.

### Listener/subscriber

```bash
PYTHONPATH=backend .venv/bin/python -m services.temperature_subscriber --write-db --output-mode verbose
```

### Dashboard bridge

```bash
PYTHONPATH=backend .venv/bin/python -m services.dashboard_bridge
```

### Event generator

```bash
PYTHONPATH=backend .venv/bin/python -m services.temperature_event_generator \
  --sensor Pod1 \
  --scenario normal \
  --count 30 \
  --interval-ms 100 \
  --seed 42 \
  --output-mode summary
```

Available scenarios are `normal`, `warning`, `recovery`, `mixed`, and
`outlier`. The generator uses `ai_worker/datasets/Test1_TempCO2O2.csv` only as
guidance for source variation; live event timestamps are generated at runtime.

### Dashboard website

In another terminal:

```bash
python3 -m http.server 8765 --directory frontend --bind 127.0.0.1
```

Open:

- <http://127.0.0.1:8765/index.html> - package entry page
- <http://127.0.0.1:8765/pages/domain-vaccine.html> - analytics dashboard
- <http://127.0.0.1:8765/pages/domain-vaccine-raw.html> - raw event stream

### Verify persistence

```bash
.venv/bin/python db/scripts/verify_persistence.py
```

## Tests and checks

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s db/tests -p 'test_*.py' -v
node --test frontend/scripts/vaccine-data.test.js
python3 -m py_compile backend/services/*.py db/scripts/*.py
node --check frontend/scripts/vaccine.js
node --check frontend/scripts/vaccine-data.js
node --check frontend/scripts/vaccine-bridge.js
node --check frontend/scripts/vaccine-raw.js
```

The convenience Makefile is under `backend/`:

```bash
make -C backend test
make -C backend reset-demo RESET_CONFIRM=YES APP_ENV=demo
```

## AI and ML material

The `ai_worker/` folder contains notebooks, saved `.pkl` models, analysis
scripts, and supporting datasets. These artifacts are included for research and
future development. They are not required to run the verified MQTT/PostgreSQL
dashboard demo, and no model is presented as a validated clinical or vaccine
disposition system.

## Experimental edge prototype

See [`edge/README.md`](edge/README.md). The prototype targets an Arduino UNO R4
WiFi and has possible support for DHT22, BMP280, optional AHT20, optional
DS3231, local Wi-Fi dashboard access, run logging, manual events, and excursion
state tracking. It is untested, standalone, and not integrated with the
verified backend pipeline.

## Documentation and research

- `docs/terminal-runbook.md` - detailed terminal procedures.
- `docs/operator-fluency.md` - how to explain one event across the system.
- `docs/presentation/` - selected current presentations.
- `docs/research/` - supporting research papers and sources.
- `docs/research_urls.doc` - research URLs used by the project.

## Safety and scope

This is an educational and research prototype. It is not a certified medical
device, compliance instrument, potency estimator, or vaccine use/discard
system. Alerts and measurements support investigation; qualified personnel and
official guidance make operational decisions.
