# Troubleshooting guide

Start with the boundary that first fails. The pipeline is generator → MQTT →
listener → PostgreSQL → dashboard bridge → browser.

## Fast checks

```bash
pg_isready -h "${POSTGRES_HOST:-localhost}" -p "${POSTGRES_PORT:-5432}"
curl -sS http://127.0.0.1:8787/health
curl -sS http://127.0.0.1:5000/health
```

The ML health check is optional. The bridge health check should report
`database_connected: true` and `read_only: true`.

## Symptoms and actions

| Symptom | Likely boundary | Action |
| --- | --- | --- |
| `pg_isready` has no response | PostgreSQL | Run `brew services start postgresql@16`; check `POSTGRES_HOST`, port, database, and local role. |
| Listener exits or reports MQTT connection error | Mosquitto | Run `brew services start mosquitto`; verify `localhost:1883`; do not start a second broker. |
| Generator reports `CSV file not found` | Source support data | Restore `ai_worker/data/Test1_TempCO2O2.csv`; the CSV is guidance, not a timestamp source. |
| Generator says `Sensor column ... not found` | CLI input | Use `--sensor Pod1` through `Pod20`, matching the source column names. |
| Generator publishes but no rows appear | Listener or database | Confirm the listener includes `--write-db`; inspect its `event_rejected` or `database_write_failed` log; run `make verify`. |
| Rows appear but dashboard is empty | Bridge/filter/browser | Check `/health`, remove restrictive query filters, and reload. The browser reads bridge responses, not PostgreSQL directly. |
| Old rows confuse a demo | Correlation/scope | Use a new `batch_id` or `make reset-dashboard`; the E2E verifier always filters by its run-specific batch ID. |
| E2E report has fewer events than requested | MQTT startup/race or listener | Ensure the listener is running before the generator; rerun `make e2e`; inspect `test-reports/e2e-latest.json` service logs. |
| E2E cannot bind port 8798 | Existing bridge/process | Stop the process using that port or run `make e2e BRIDGE_PORT=...` after adding the corresponding Make variable. |
| Timestamps look historical | Incorrect assumption about CSV | Inspect `event_time`, `received_at`, and `stored_at`; current events use UTC creation time. |
| ML tab says unavailable | Model service/artifact | Run `make train-models`, then `make start-ml-service`; ML is advisory and not required for monitoring. |

## Read the structured logs

The listener emits JSON log events for `event_persisted`, `event_rejected`, and
`database_write_failed`. The generator's summary includes requested, generated,
published, failed, scenario, phase, and throughput counts. Keep these outputs
with the E2E reports when diagnosing a failed run.

## Safety boundaries

The reset command deletes and recreates application tables. It requires an
explicit confirmation, a development/demo/test environment, and a local
PostgreSQL host. The dashboard bridge is read-only; a `POST` request should
return `405` rather than mutate data.
