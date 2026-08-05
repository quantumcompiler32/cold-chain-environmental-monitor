# Database

This folder contains the canonical PostgreSQL bootstrap schema, legacy
migrations, guarded reset tools, read-only verification tools, SQL queries, and
database tests. `bootstrap/001_core.sql` creates the current schema;
`migrations/` is only for an existing legacy database.

```bash
psql -d iotdb -f db/bootstrap/001_core.sql
APP_ENV=demo RESET_CONFIRM=YES python3 db/reset_demo.py --confirm-reset
python3 db/verify_database.py
python3 db/verify_persistence.py
```
