# PostgreSQL Setup

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Automatic initialization

```bash
iot setup
```

To rerun only the database script:

```bash
iot db-init
```

The initialization script is idempotent. Running it again does not delete existing telemetry rows.

## Database objects

Database:

```text
iot_platform
```

Main table:

```sql
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(150) NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    temperature NUMERIC(7, 2),
    humidity NUMERIC(7, 2),
    pressure NUMERIC(9, 2),
    status VARCHAR(30) NOT NULL DEFAULT 'online',
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Views:

- `v_latest_telemetry` — newest rows first.
- `v_device_summary` — count and averages by device.

## Simple PostgreSQL commands

```bash
iot postgres      # Open psql
iot see           # Show newest 10 rows
iot watch         # Refresh newest rows every 3 seconds
iot count         # Count all rows
iot devices       # Summarize each device
iot schema        # Describe telemetry_logs
iot tables        # List tables and views
iot query "SELECT * FROM v_device_summary;"
```

## Useful psql commands

| Command | Meaning |
|---|---|
| `\l` | List databases |
| `\c iot_platform` | Connect to the project database |
| `\dt` | List tables |
| `\dv` | List views |
| `\d telemetry_logs` | Show table schema |
| `\q` | Exit psql |

## Schema modification examples

```sql
ALTER TABLE telemetry_logs ADD COLUMN battery_voltage NUMERIC(5, 2);
ALTER TABLE telemetry_logs ALTER COLUMN device_id TYPE VARCHAR(200);
UPDATE telemetry_logs SET status = 'online' WHERE status = 'active';
```

## Safe clearing

```bash
iot clear
```

The command requires typing `CLEAR` before truncating rows and resetting the identity counter.

---

Operations: [[Database Operations]] · Troubleshooting: [[PostgreSQL Problems]]
