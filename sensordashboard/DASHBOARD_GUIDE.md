# Dashboard guide

The dashboard is a read-only PostgreSQL client.

It displays:

- total stored events;
- number of sensors represented in the database;
- out-of-range event count;
- event status counts;
- every stored event in a simple table.

The page polls `dashboard_bridge.py` every five seconds. The bridge performs a
read-only PostgreSQL transaction and exposes:

- `GET /health`
- `GET /api/events`
- `GET /api/events/export.csv`

There are no dashboard controls for the generator, MQTT, or PostgreSQL writes.
Start those independent services from the terminal using
[SIMPLE_RUNBOOK.md](SIMPLE_RUNBOOK.md).
