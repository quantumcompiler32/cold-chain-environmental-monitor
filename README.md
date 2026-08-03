# Vaccine Cold-Chain Monitor

This is a small, self-contained handoff package for the vaccine cold-chain
dashboard. The verified demo runs locally:

```text
event generator -> Mosquitto MQTT -> subscriber -> PostgreSQL -> dashboard bridge -> frontend
```

## Package layout

- `frontend/` - dashboard HTML, JavaScript, and CSS.
- `backend/` - generator, subscriber, bridge, and backend helpers.
- `db/` - schema, reset files, and the verification query.
- `ai_worker/` - one analysis notebook, generated models, and project datasets.
- `edge/` - experimental Arduino UNO R4 WiFi firmware and setup files.
- `docs/` - final report, presentations, research paper, URLs, and dataset notes.

## Run the verified demo

Install Python dependencies from this project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Start PostgreSQL and Mosquitto locally, then reset the demo database:

```bash
APP_ENV=demo .venv/bin/python db/reset_demo.py --confirm-reset
```

Run these commands in separate terminals:

```bash
PYTHONPATH=backend .venv/bin/python -m temperature_subscriber --write-db --output-mode verbose
```

```bash
PYTHONPATH=backend .venv/bin/python -m dashboard_bridge
```

```bash
PYTHONPATH=backend .venv/bin/python -m temperature_event_generator \
  --sensor Pod1 --scenario normal --count 30 --interval-ms 100 --seed 42 \
  --output-mode summary
```

Serve the frontend in another terminal:

```bash
python3 -m http.server 8765 --directory frontend --bind 127.0.0.1
```

Open:

- <http://127.0.0.1:8765/index.html>
- <http://127.0.0.1:8765/domain-vaccine.html>
- <http://127.0.0.1:8765/domain-vaccine-raw.html>

Verify persisted data with:

```bash
.venv/bin/python db/verify_persistence.py
```

The generator uses built-in deterministic guidance by default, so the demo
does not require a raw CSV. An external CSV can still be supplied with
`--csv-file` when needed.

## AI and edge work

The `ai_worker/` contents are supporting research and future development. The
saved models are not validated clinical or vaccine-disposition systems.

The `edge/` contents are an untested standalone Arduino UNO R4 WiFi prototype.
See [`edge/README.md`](edge/README.md) for hardware, libraries, and upload
information. It is not required for the verified local demo.

## Documentation

The final report, presentations, research paper, research URLs, and dataset
notes are under `docs/`. The package is an educational prototype, not a
certified medical device or compliance instrument.
