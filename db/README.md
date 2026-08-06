# Database

This folder contains the canonical PostgreSQL bootstrap schema, legacy
migrations, and guarded reset tools. `bootstrap/001_core.sql` creates the current schema;
`migrations/` is only for an existing legacy database.

```bash
psql -d iotdb -f db/bootstrap/001_core.sql
APP_ENV=demo RESET_CONFIRM=YES python3 db/reset_demo.py --confirm-reset
```

## File guide

| File | Purpose |
|---|---|
| `__init__.py` | Marks `db` as a Python package. |
| `bootstrap/001_core.sql` | Creates the canonical PostgreSQL tables and indexes. |
| `bootstrap/README.md` | Explains the clean bootstrap schema. |
| `migrations/001_legacy_temperature_events_to_vaccine.sql` | Migrates legacy event tables to the vaccine schema. |
| `migrations/002_remove_source_time.sql` | Removes obsolete source-time fields. |
| `migrations/003_add_domain_state_fields.sql` | Adds operational status, severity, and alert fields. |
| `migrations/004_add_run_id_correlation.sql` | Adds run ID correlation to event tables. |
| `migrations/README.md` | Explains when and how to use migrations. |
| `reset/reset_demo.sql` | Destructive SQL used to remove demo tables. |
| `reset_demo.py` | Safely resets the demo database with environment guards. |
| `reset_dashboard.py` | Resets dashboard demo data. |
