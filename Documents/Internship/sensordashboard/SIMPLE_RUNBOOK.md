# Simple runbook

## Dashboard

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python dashboard_bridge.py
```

In another terminal:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/index.html`, select Vaccine Cold Chain, and use
the top switcher.

## Live run

1. Open **Live runner**.
2. Select one or more Pods.
3. Select one or more scenarios.
4. Set the interval and events per scenario per Pod.
5. Optionally upload a CSV. It must have `date`, `time`, and selected Pod columns.
6. Press **Start live run**. Press **Stop** whenever needed.

Total events requested:

```text
Pods x scenarios x events per scenario per Pod
```

Analytics and Raw events update while the bridge receives MQTT events. Raw
events autoscrolls to the newest event unless you turn that off.

## PostgreSQL

Apply the safe additive schema migration before saving events:

```bash
psql -U mokshjoshi -d iotdb -f create_temperature_table.sql
```

The migration adds uncertainty columns and keeps existing `temperature_c` and
`status` values unchanged. The paper's Type-T accuracy is approximately
`+/-0.5 C`; it is not the vaccine storage range.

Run the subscriber with database writes:

```bash
python temperature_subscriber.py --write-db
```

Run the read-only report:

```bash
python analyze_temperature_database.py
```

The report includes raw status counts, borderline counts, near-threshold
counts, and the percentage of readings whose uncertainty interval crosses a
storage boundary.

## Command-line scenarios

```bash
python temperature_event_generator.py --sensor Pod1 --scenario normal --max-events 20
python temperature_event_generator.py --sensor Pod1 --scenario outlier --max-events 40
python temperature_event_generator.py --sensor Pod1 --scenario failure --max-events 20
python temperature_event_generator.py --sensor Pod1 --scenario recovery --max-events 20
```

For Moderna, provide both bounds:

```bash
python temperature_event_generator.py --sensor Pod1 --vaccine-type moderna --min-temp -50 --max-temp -15 --scenario normal --max-events 20
```

More detail is in [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) and
[SCENARIOS.md](SCENARIOS.md).
