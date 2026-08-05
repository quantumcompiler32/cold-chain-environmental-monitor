# Aug 4 final independent verification report

Date: 2026-08-04
Scope: the maintained sensor-dashboard project (the repository root on GitHub;
`/Users/mokshjoshi/Documents/Internship/sensordashboard` locally)
Review rule: a criterion without direct evidence is `FAIL`.

## Verdict

The persisted MQTT-to-PostgreSQL-to-dashboard path is proven for the latest
deterministic run. The cleanup removes the legacy flat-root application,
separate prototype tree, and unused prototype dashboard assets. All local
tests pass, including the opt-in PostgreSQL integration suite. The scoped
commit is pushed to GitHub and the local/remote branch hashes match.

## Acceptance table

| # | Criterion | Result | Evidence |
|---:|---|---|---|
| 1 | Repository structure is coherent and reproducible | **PASS** | The maintained layout is `frontend/`, `db/`, `backend/`, `ai_worker/`, `edge/`, and `docs/`, with tests kept beside the owning package. README/runbooks use repository-relative commands, website port `8766`, and API port `8787`. |
| 2 | Local code and committed deliverables are aligned | **PASS** | The maintained source, canonical data fixture, comments, docs, and tests are committed on `quant` at `02f63fd` and pushed to GitHub; the scoped project comparison against `origin/quant` is empty. |
| 3 | Every process has a documented command and responsibility | **PASS** | `docs/architecture-and-pipeline.md` has the component responsibility table; `docs/database-access.md` has the read/write ledger; `README.md`, `docs/setup-and-runbook.md`, and `docs/terminal-runbook.md` provide commands for PostgreSQL, Mosquitto, listener, bridge, web server, generator, and optional ML service. |
| 4 | Generator → listener → database path is proven | **PASS** | `make e2e` passed all five manifest cases through public process boundaries. The run generated and the bridge observed 26 events; PostgreSQL contains 26 current-run domain rows and 26 matching generic rows. |
| 5 | Database writer is identified | **PASS** | `docs/database-access.md` identifies `backend.temperature_subscriber` with `--write-db` as the normal write owner. `backend/temperature_subscriber.py:176-272` inserts both projections transactionally and emits `pg_notify` after commit. |
| 6 | Dashboard reader is genuinely read-only | **PASS** | `DatabaseReader` executes `SET TRANSACTION READ ONLY`; bridge `POST`/`PUT`/`PATCH`/`DELETE` return `405`. Direct `POST /api/events` returned `405`, `Allow: GET, OPTIONS`, and `The dashboard bridge is read-only.` |
| 7 | Latest-N query proves current events reached PostgreSQL | **PASS** | Direct `SELECT ... ORDER BY stored_at DESC, event_id DESC LIMIT 5` returned current-run event IDs, `event_time`, `received_at`, `stored_at`, batch IDs, and statuses. `make verify-fast` returned `latest_run_id=e2e-20260805T005534-0e0bbd3c` and `read_only=true`. |
| 8 | HTTP routes and static assets have no unexplained 404s | **PASS** | `/health`, `/ready`, `/api`, API events, analytics, and CSV returned expected responses. A page requested on the API port returned a documented diagnostic 404 pointing to the website port. All 26 maintained web files returned `200`; all local HTML asset references resolved. |
| 9 | CSV is correctly described and tested | **PASS** | README and architecture docs describe CSV as source-variation guidance, not the live event timestamp. `test_exports_new_event_columns_deterministically` passed. Direct filtered export returned `200`, `text/csv`, a download disposition, the canonical header, and 4 data rows. |
| 10 | Analytics filters work | **PASS** | Python bridge filter tests passed. Direct `/api/analytics?batch=...-mixed&severity=critical` returned count `4`, `CRITICAL:4`, `cooling_failure:3`, `recovery:1`, and the applied filter scope. |
| 11 | Units, timestamps, aggregation intervals, and moving-average windows display correctly | **PASS** | `vaccine-data.test.js` passed unit/timezone formatting and hourly aggregation with a three-point trailing average. The page exposes Celsius/Fahrenheit, raw/15-minute/hourly/daily intervals, and 3-/5-point trailing windows with definitions in `vaccine-data.js`. |
| 12 | Latest recorded data is distinct from historical average | **PASS** | The page labels “Latest” and “Period average” separately; the JavaScript test `keeps latest recorded temperature separate from period average` passed with different values. |
| 13 | Raw-event rules produce warning, critical, stale, and recovery states | **PASS** | E2E observed `WARNING`/`TEMPERATURE_BOUNDARY_RISK`, `CRITICAL`/`VACCINE_SAFE_RANGE_VIOLATION`, and `RECOVERY`/`TEMPERATURE_RECOVERY`. `test_old_event_is_stale` proves `STALE`/`EVENT_STALE` after five minutes. The dashboard maps and displays both new states. |
| 14 | Unit, integration, and end-to-end tests pass | **PASS** | `make test`: 48/48 passed with 5 expected sandbox skips. `RUN_DB_INTEGRATION=1 ... unittest discover`: 48/48 passed. Node: 19/19 passed. `make e2e`: 5/5 cases passed. |
| 15 | Documentation uses actual final filenames and commands | **PASS** | The maintained filenames are documented in `README.md`, `docs/architecture-and-pipeline.md`, `docs/database-access.md`, `docs/setup-and-runbook.md`, `docs/terminal-runbook.md`, `docs/end-to-end-verification.md`, and `docs/troubleshooting.md`. Commands use `8766` for pages and `8787` for the API; no maintained references to removed archive/prototype paths remain. |
| 16 | No inference work displaced unfinished baseline requirements | **PASS** | Inference remains explicitly optional, while the baseline pipeline, read-only dashboard, current-event verification, and warning/critical/stale/recovery rules are implemented and tested. |

## Deterministic E2E evidence

Command:

```bash
cd "$(git rev-parse --show-toplevel)"
make e2e
```

Generated report: `test-reports/e2e-latest.json` and
`test-reports/e2e-latest.md`.

Run ID: `e2e-20260805T005534-0e0bbd3c`
Total generated/observed: `26/26`
Generator failures: `0`

Runtime note: the first `make e2e` attempt failed before starting cases because
PostgreSQL and Mosquitto were unavailable. The documented Homebrew service
command then failed with Homebrew's `undefined method 'stop_timeout'` error.
After approval, the local `pg_ctl` and `mosquitto` binaries were started
directly and the same deterministic E2E command passed. The clean documented
infrastructure bootstrap therefore remains an environment-level risk.

| Scenario | Expected | Observed | Verified behavior |
|---|---:|---:|---|
| normal | 4 | 4 | `ACCEPTABLE`; correlated batch/run |
| warning | 4 | 4 | `ACCEPTABLE`, operational `WARNING`, `TEMPERATURE_BOUNDARY_RISK` |
| recovery | 5 | 5 | first `TOO_WARM`/`CRITICAL`, later in-range rows `RECOVERY` |
| mixed | 9 | 9 | phase sequence normal → cooling_failure → recovery; recovery rows explicit |
| outlier | 4 | 4 | `TOO_COLD` and `TOO_WARM`, all `CRITICAL` |

## Database evidence

Commands:

```bash
make verify-fast
make verify
psql -h 127.0.0.1 -p 5432 -d iotdb -F '|' -Atqc \
  "SELECT event_id, event_time, received_at, stored_at, run_id, batch_id,
          scenario, status, operational_status
   FROM vaccine_temperature_events
   WHERE run_id = 'e2e-20260805T005534-0e0bbd3c'
   ORDER BY stored_at DESC, event_id DESC LIMIT 5"
```

Observed from `make verify-fast`:

```text
database_connected=true
generic_count=964
domain_count=964
latest_run_id=e2e-20260805T005534-0e0bbd3c
orphan_domain_count=0
orphan_generic_count=0
read_only=true
ready=true
```

Observed current-run counts:

```text
mixed   9
normal  4
outlier 4
recovery 5
warning 4
domain=26, generic=26, orphan_domain=0
```

The latest-N query returned the newest outlier rows with event times from the
E2E run and stored times immediately afterward, including `TOO_WARM` and
`TOO_COLD` rows with `operational_status=CRITICAL`. The newest mixed recovery
row had `operational_status=RECOVERY` and `rule_alert=TEMPERATURE_RECOVERY`.

## Endpoint and asset evidence

Temporary local servers were started using the documented commands. Observed:

- `/health`: `200`, bridge `read_only=true`.
- `/ready`: `200`, `database_connected=true`, `read_only=true`.
- `/api`: `200` with the documented route list.
- `/api/events?batch=e2e-...-mixed`: `9` events from PostgreSQL.
- `/api/analytics?batch=e2e-...-mixed&severity=critical`: `4` events with expected phase counts.
- `/api/events/export.csv?batch=e2e-...-outlier`: `200`, CSV content type, attachment disposition, 4 data rows.
- `POST /api/events`: `405` with the read-only message.
- `/api/live/stream`: `200` SSE snapshot with `source=postgresql` and the current-run events.
- Website sweep: 26 files checked, `0` static failures; HTML reference sweep: `0` missing references.
- API-port request for `/pages/domain-vaccine.html`: `404` with an explicit hint that pages belong on port `8766`; the same page on the static server returned `200`.

## Test results

```text
make test                                      48 tests, OK, 5 expected sandbox skips
RUN_DB_INTEGRATION=1 ... unittest discover    48 tests, OK
node --test frontend/tests/*.test.js              19 tests, pass 19, fail 0
make e2e                                       5 cases passed, status=passed
```

## Unresolved risks and required follow-up

1. GitHub recommends Git LFS for the 60.98 MB CSV fixture because it exceeds
   the recommended 50 MB file size; the current remote branch is valid and the
   fixture is intentionally retained for deterministic local replay.
2. Homebrew's service wrapper previously failed with an internal
   `stop_timeout` error; direct local PostgreSQL/Mosquitto startup remains the
   documented environment fallback if that wrapper recurs.
