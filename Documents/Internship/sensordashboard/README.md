# Vaccine cold-chain dashboard

This folder contains a small, read-only dashboard for the temperature event
pipeline.

```text
Event generator → Mosquitto MQTT → database subscriber → PostgreSQL
                                                        ↓
                                             read-only dashboard adapter
                                                        ↓
                                                     index.html
```

The generator is the simulated remote edge device. The dashboard never starts
or stops it, connects to MQTT, or writes to PostgreSQL. It polls the adapter
for all stored events and can export all stored rows as a CSV for Colab.

## Dashboard

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m http.server 8765 --bind 127.0.0.1
```

Open <http://127.0.0.1:8765/index.html>.

The central `index.html` loads the project page `domain-vaccine.html`. The
project page reads PostgreSQL through `dashboard_bridge.py`, shows simple event
summaries and the stored-event table, and exports `temperature_events.csv`.

## Services

Use [SIMPLE_RUNBOOK.md](SIMPLE_RUNBOOK.md) for the complete terminal startup.
The independent services are:

- `temperature_event_generator.py`: publishes sensor events to MQTT.
- `temperature_subscriber.py`: validates MQTT events and inserts them into PostgreSQL.
- `dashboard_bridge.py`: performs read-only PostgreSQL queries for the browser.

## Tests

```bash
node --test test/vaccine-data.test.js
python3 -m unittest discover -s test -p 'test*.py'
```
