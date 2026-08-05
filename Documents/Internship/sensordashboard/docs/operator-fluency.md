This guide is for explaining the project in a meeting. The goal is to be able
to trace one event through every boundary and explain what each timestamp,
table, query, API response, and dashboard state means.

## The one-event explanation

1. The generator reads a CSV row only for temperature shape and event guidance.
2. It creates a new UUID `event_id`, current UTC `event_time`, Pod, vaccine,
   scenario, temperature, status, and uncertainty fields.
3. It serializes the event and publishes it to Mosquitto on
   `devices/temperature`.
4. The listener receives the message and records `received_at` immediately.
5. It validates required fields and recalculates uncertainty values so a sender
   cannot claim a contradictory range or status.
6. One PostgreSQL transaction inserts the generic raw JSON record and the
   flattened vaccine record using the same `event_id`.
7. PostgreSQL records `stored_at`. If either insert fails, the transaction rolls
   back both writes. If the same event is delivered again, the unique event ID
   makes processing idempotent.
8. The read-only bridge queries the flattened vaccine table, calculates
   ingestion latency and event age, serializes values for JSON, and returns
   them to the browser.
9. The browser normalizes the API payload, maps status to readable labels, and
   renders the operational dashboard. It never receives database credentials.

## Backend questions you should be able to answer

### Why are there two tables?

`telemetry_logs` preserves the generic raw-event design and untouched payload.
`vaccine_temperature_events` is the domain read model: one flattened row per
vaccine event so queries and dashboard filters do not repeatedly unpack JSON.

### Why is `event_time` not the CSV time?

The CSV is guidance for the simulator. A simulated event represents something
created now, so `event_time` is current UTC. The CSV timestamp is not included
in the live event contract and cannot be used to decide whether the event is
fresh.

### Why do `received_at` and `stored_at` differ?

They identify two operational boundaries. The difference between
`received_at` and `event_time` is ingestion latency; the difference between
`CURRENT_TIMESTAMP` and `event_time` is event age. `stored_at` tells us when
the transaction completed.

### What happens if the second insert fails?

The listener uses one transaction. PostgreSQL rolls back the generic and
vaccine writes together, so the dashboard cannot see a half-persisted event.

### What makes duplicate delivery safe?

The generator places a stable UUID in the event. Both tables enforce that ID
uniquely, and inserts use conflict-safe behavior. Re-delivery is reported as a
duplicate instead of creating a second event.

### What does the verification command prove?

It proves that the database has fresh rows, not merely that the dashboard
process is running. It shows the newest IDs and timestamps, latency, age, total
count, and first/latest event times.

## Frontend questions you should be able to answer

### Why does the browser use a bridge?

The browser is a read-only client. The bridge keeps PostgreSQL credentials and
SQL on the server side, enforces read-only transactions, and exposes a small
JSON/CSV interface.

### Where is timestamp formatting done?

The database stores native timezone-aware timestamps. The bridge serializes
them for JSON, and the UI chooses human-readable formatting. No UI label is
used as the source of truth for event freshness.

### What happens when PostgreSQL is offline?

The bridge reports the unavailable state. The browser shows a truthful offline
or no-data state rather than inventing readings.

### Why do the dashboard and verification query sometimes differ in order?

The verification query is newest-first for an operator check. The API can keep
chronological order for trend rendering and explicitly supplies event times;
the frontend sorts using event time and stable event ID.

## Meeting demo script

For each scenario, say what you expect before running it:

```text
1. Reset the local/demo database.
2. Start Mosquitto and PostgreSQL.
3. Start the listener with --write-db.
4. Run one named generator scenario with --count, --seed, and --output-mode summary.
5. Run `python3 db/verify_persistence.py` and point out current event_time values and ingestion latency.
6. Open the dashboard and explain how the API response becomes the displayed state.
7. Repeat for the next isolated scenario.
```

Recommended runs:

```bash
APP_ENV=demo python3 db/reset_demo.py --confirm-reset
python3 -m backend.temperature_event_generator --scenario normal --count 30 --seed 42 --output-mode summary
python3 db/verify_persistence.py

APP_ENV=demo python3 db/reset_demo.py --confirm-reset
python3 -m backend.temperature_event_generator --scenario recovery --count 30 --seed 42 --output-mode summary
python3 db/verify_persistence.py

APP_ENV=demo python3 db/reset_demo.py --confirm-reset
python3 -m backend.temperature_event_generator --scenario mixed --count 30 --seed 42 --output-mode summary
python3 db/verify_persistence.py
```

Use `--scenario outlier` when you want every generated event to be outside the
safe range. The generator alternates between too cold and too warm readings.

ML is not part of this rehearsal. The important story is current event
creation, reliable persistence, verification, and truthful dashboard display.
