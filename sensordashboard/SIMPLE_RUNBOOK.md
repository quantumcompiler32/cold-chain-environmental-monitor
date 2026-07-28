# Simple runbook

Run each command in its own Terminal tab. Create the virtual environment once
when starting a new session, then activate it in every Python service tab.

## 1. Create the environment

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## 2. Start PostgreSQL and Mosquitto

```bash
brew services start postgresql@16
brew services start mosquitto
```

## 3. Prepare the database

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
psql -U mokshjoshi -d iotdb -f create_temperature_table.sql
```

## 4. Start the database subscriber

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 temperature_subscriber.py --write-db
```

## 5. Start the event generator

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 temperature_event_generator.py \
  --sensor Pod1 \
  --vaccine-type pfizer_ultralow \
  --scenario normal \
  --interval-ms 500 \
  --max-events 20
```

Run additional generator commands in separate tabs when you want more Pods or
scenarios. The dashboard does not run these commands.

## 6. Start the read-only dashboard adapter

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
source .venv/bin/activate
python3 dashboard_bridge.py
```

## 7. Serve the pluggable dashboard

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m http.server 8765 --bind 127.0.0.1
```

Open <http://127.0.0.1:8765/index.html>.

## Export for Colab

Click **Export all events CSV** in the dashboard. The adapter reads every row
from PostgreSQL and downloads `temperature_events.csv`.

## Stop

Press `Ctrl+C` in the subscriber, generator, adapter, and web-server tabs.
Stop the background services only when you are finished:

```bash
brew services stop mosquitto
brew services stop postgresql@16
```
