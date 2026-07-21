# Database Operations

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Retrieve data

```bash
iot see
```

Show a different number of rows:

```bash
iot recent 25
```

Continuously refresh:

```bash
iot watch
```

## Summaries

```bash
iot count
iot devices
```

## Open PostgreSQL

```bash
iot postgres
```

## Run custom SQL

```bash
iot query "SELECT device_id, MAX(timestamp) FROM telemetry_logs GROUP BY device_id;"
```

## Export data

```bash
iot save
```

Output format:

```text
exports/telemetry_YYYYMMDD_HHMMSS.csv
```

Preview the latest export:

```bash
iot latest
```

Open the export folder:

```bash
iot exports
```

## Clear rows

```bash
iot clear
```

This requires explicit confirmation.

## Recreate missing objects without deleting data

```bash
iot db-init
```

---

Related: [[PostgreSQL Setup]] · [[Export and Upload Data]]
