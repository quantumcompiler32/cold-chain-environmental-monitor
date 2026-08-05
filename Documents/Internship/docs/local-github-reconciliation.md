# Local/GitHub reconciliation — Phase 3

Snapshot taken 2026-08-04 in `/Users/mokshjoshi/Documents/Internship`.

This is an inventory and preservation record. During this phase I did not reset,
restore, clean, pull, merge, rebase, overwrite, stage, or remove anything. The
only permitted worktree edit is this file.

## Scope and verified Git state

The Git worktree root is `/Users/mokshjoshi`, not the Internship directory.
That root also contains personal home-directory files, so a raw repository
status includes unrelated material. The application scope is:

- `/Users/mokshjoshi/Documents/Internship/sensordashboard`
- `/Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project`
- Internship domain and agent documentation that is tracked or locally present.

The last locally cached remote state is the best available GitHub comparison:

| Item | Observed value |
| --- | --- |
| Current branch | `quant` |
| Current commit | `aaa6c3c` — Add Workstream D documentation and E2E verification |
| Current branch upstream | None |
| Cached remote branch | `origin/main` at `f788471` — Simplify vaccine handoff package (#3) |
| Cached divergence | `quant` is 42 commits ahead and 5 commits behind `origin/main` |
| Fresh remote check | Blocked: `git remote show origin` could not resolve `github.com` |
| Staged changes | None |
| Unstaged tracked paths | 40 total: 29 deletions and 11 modifications across the full worktree |
| Untracked paths in `sensordashboard` | 32 |
| Untracked paths in `Documents/Internship` | 576, including 32 in `sensordashboard` |
| Untracked paths in adjacent IoT project | 34 |

The remote branch is not a newer source of truth by assumption. It is a
different handoff layout: the cached `origin/main` tree has `backend/`, `db/`,
`frontend/`, `edge/`, `ai_worker/`, and root `docs/`, while local `quant` has
the maintained application under `Documents/Internship/sensordashboard/`.
The two layouts must be reconciled intentionally after this phase.

## Recent local-only remediation commits

These commits exist in the local `quant` history and are not in cached
`origin/main`. They are protected local work even though they are already
committed locally.

| Workstream | Local evidence | State relative to cached GitHub | Classification | Planned action |
| --- | --- | --- | --- | --- |
| Agent A — pipeline, PostgreSQL, API | `0c4991a` at 2026-08-04 13:03; prerequisites include `2d8076b`, `a505728`, `0b71ba3`, `587ae0b` | Present locally but not pushed | Required application source, tests, database assets, and docs | Preserve and merge with remote |
| Agent B — analytics dashboard | `b22c99d` at 2026-08-04 12:58 | Present locally but not pushed | Required application source and dashboard tests | Preserve and merge with remote |
| Agent C — raw events and alerts | No dedicated Workstream C commit; warning/critical rules and recovery scenario are in `a505728`, `587ae0b`, and current dashboard files | Partial, local only | Required application source, but incomplete | Preserve and merge with remote after stale/recovery decision |
| Agent D — documentation and E2E | `aaa6c3c` at 2026-08-04 13:07; local report added afterward | Present locally but not pushed | Required documentation, E2E script, manifest, and tests | Preserve and merge with remote |
| Optional ML/inference slice | `99f583a`, `4c544b8`, `74cc58d`, `7952760` | Present locally but not pushed | Required application source only if the optional ML scope is retained | Preserve and merge with remote after baseline raw-state requirements are closed |

## Required file inventory

“Exists on GitHub” below means exists in the cached `origin/main` tip or in
the local `quant` commit history, as noted; it does not claim a fresh network
fetch. “Local newer” means newer than the cached remote version or a newer
local working-tree edit was observed.

| File | Git state | Local change summary | Requirement addressed | Exists on GitHub | Local newer | Required | Contains secrets | Tests covering it | Planned action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sensordashboard/services/{dashboard_bridge,event_contract,temperature_event_generator,temperature_subscriber,temperature_uncertainty}.py` | committed on `quant` | A atomic MQTT → PostgreSQL write path, run correlation, current UTC timestamps, read-only bridge, latest-N verification | Agent A pipeline, PostgreSQL writer, database table usage, read-only API, correlation | No in cached `origin/main` layout; yes in local history | Yes | Yes | No secret pattern found | 46 Python tests; 19 JS tests; prior E2E report | Preserve and merge with remote |
| `sensordashboard/database/{bootstrap,migrations,reset,verification}/**` | committed on `quant` | Canonical schema, migrations, reset guards, latest-event SQL | Agent A database usage and latest-N verification | No in cached `origin/main` layout | Yes | Yes | No | `test_database_assets`, reset-guard tests, prior E2E report | Preserve and merge with remote |
| `sensordashboard/web/{pages,scripts,styles}/**` | committed on `quant` | Analytics filters, intervals, moving average, CSV export, labels, raw display, inference UI | Agents B/C; Phase 1 UI | No in cached `origin/main` layout; equivalent older frontend exists remotely | Yes | Yes | No secret pattern found | 19 JS tests; dashboard bridge/HTTP tests | Preserve and merge with remote |
| `sensordashboard/tests/**`, `phase1-stitch-ui/**/*.test.js` | committed on `quant` | Pipeline, analytics, alert-rule, inference, accessibility, and E2E asset coverage | Agents A–D | No in cached `origin/main` layout | Yes | Yes | No | `make test`, Node tests, prior E2E report | Preserve and merge with remote |
| `sensordashboard/docs/{architecture-and-pipeline,data-dictionary,database-access,demo-script,end-to-end-verification,setup-and-runbook,troubleshooting,presentation-update-checklist,operator-fluency}.md` | committed on `quant` | Architecture, pipeline, data dictionary, runbook, troubleshooting, demo, E2E and presentation evidence | Agent D documentation | No in cached `origin/main` layout | Yes | Yes | No | Documentation asset tests and prior E2E report | Preserve and merge with remote |
| `sensordashboard/docs/terminal-runbook.md` | modified, 55 additions / 362 deletions | Replaced the older detailed runbook with the shorter canonical command sequence; uses web port `8766` | Agent D runbook and reproducible demo | No in cached `origin/main` layout | Yes | Yes | No | Existing docs; not independently rerun | Preserve and merge with remote |
| `sensordashboard/docs/final-verification-report.md` | untracked, 2026-08-04 | Independent acceptance report; records passes, structure mismatch, port mismatch, and missing explicit stale/recovery states | Agent D final verification reporting | No | Yes | Yes | No | Report cites 46 Python, 29 prior Node, 5/5 prior E2E; current Node run is 19 tests | Preserve and commit |
| `sensordashboard/archive/data/Test1_TempCO2O2.csv` | untracked; exact byte copy of deleted tracked CSV | Moved source-variation data into the archive support area | Required generator input; generator now hard-codes this path | No | Yes | Yes | No | Generator scenario tests; required by E2E/demo | Preserve and commit |
| `sensordashboard/archive/database/create_temperature_table.sql` | untracked; exact byte copy of deleted tracked SQL | Moved legacy schema helper into archive | Historical/reference database support | No | Yes | Reference only | No | Not part of current canonical bootstrap tests | Preserve and merge with remote |
| `sensordashboard/archive/docs/{DASHBOARD_GUIDE,SCENARIOS,SIMPLE_RUNBOOK}.md` | untracked; relocated legacy docs, content differs from original tracked versions | Preserved older guides under archive | Historical documentation and provenance | No | Yes | Reference only | No | No current automated coverage | Preserve and merge with remote |
| `sensordashboard/archive/tests/{python,javascript}/**` | untracked; relocated legacy tests, not identical to current tests | Preserved pre-remediation tests | Historical test provenance | No | Yes | No until reviewed | No | Not run; current tests live under `tests/` and `web/scripts/` | Investigate further |
| `sensordashboard/archive/artifacts/stitch-upload-package/**` and `stitch-*.zip` | untracked, 16 source/reference files plus 2 ZIPs | Design brief, screenshots, paper PDF, upload manifest, and packaged references | Design provenance, not runtime execution | No | Yes | No for runtime | No secret pattern found; includes source PDF and images | No automated coverage | Preserve outside Git because it is local configuration/reference |
| Deleted legacy flat application set listed below | unstaged deletions; 29 paths | Removed duplicate/obsolete top-level copies while newer `services/`, `database/`, `web/`, `tests/`, and archive locations remain | Intended structure cleanup, but not yet proven as a safe rename | Cached `origin/main` has an equivalent older handoff tree, not these paths | Local working tree is newer but uncommitted | Yes, until rename mapping is verified | No secret pattern found | Current tests cover the replacement paths; no deletion safety test | Preserve and merge with remote after backup and reference audit |
| `CONTEXT.md` | tracked, 57 additions | Added vaccine cold-chain glossary and ML/read-only domain boundaries | Required domain documentation for the remediation | No in cached `origin/main` | Yes | Yes | No | Documentation review; no automated test | Preserve and commit |
| `Obsidian Vault/.obsidian/{appearance,workspace}.json` | tracked modifications | Local Obsidian UI/workspace state and formatting changes | Local vault environment, not application runtime | No in cached `origin/main` | Yes | No | No | None | Preserve outside Git because it is local configuration |
| `Obsidian Vault/ByteSmart Command Center.md` | tracked modification | Updated local refresh timestamp | Local vault status | No in cached `origin/main` | Yes | No | No | None | Preserve outside Git because it is local configuration |
| `Obsidian Vault/.obsidian/graph.json` | untracked | Obsidian-generated graph state | Local vault runtime artifact | No | Yes | No | No | None | Preserve outside Git because it is local configuration |
| `Projects/iot_workspace/projects/temperature_iot_project/dashboard_bridge.py` | tracked modification, 189 additions / 30 deletions | Separate older/parallel bridge gained upload handling, multi-profile/scenario workers, uncertainty enrichment, cleanup, and run coverage | Possible Agent A/C application source, but separate from maintained `sensordashboard` package | Not present in cached `origin/main` layout | Yes | Unknown | No secret pattern found | No current `sensordashboard` test imports this path | Investigate further |
| `Projects/iot_workspace/projects/temperature_iot_project/**` untracked companion tree | 34 untracked paths | Alternate complete local project with its own bridge, generator, frontend, data, tests, env files, and docs | Possible duplicate application or separate experiment | No | Unknown | Unknown | `.env` not present in this candidate tree; ignored env/runtime folders exist | Not run | Investigate further |
| `Documents/Internship/.agents/**`, `AGENTS.md`, `docs/agents/**`, `docs/adr/0003–0006`, `docs/specs/**` | untracked local instructions/domain docs | Agent skill packs, repository instructions, ADRs, and vaccine UI spec used by this workspace | Local collaboration and domain context | No in cached `origin/main` | Unknown | Required for this local agent workflow; not necessarily application deliverables | No secret pattern found | None | Preserve outside Git because it is local configuration, unless separately approved for repository commit |
| `sensordashboard/.venv/`, `models/`, `test-reports/`, `**/__pycache__/`, `.DS_Store` | ignored | Python environment, generated model bundle/metadata, E2E reports, bytecode, and macOS metadata | Runtime/build artifacts | No | N/A | No | No secret pattern found | Tests generated or use some of these artifacts | Preserve outside Git because it is local configuration |

### Deleted flat paths requiring explicit rename verification

These are all 29 unstaged deletions. They must not be removed from the final
deliverable until every reference and replacement has been verified:

```text
sensordashboard/DASHBOARD_GUIDE.md
sensordashboard/SCENARIOS.md
sensordashboard/SIMPLE_RUNBOOK.md
sensordashboard/Test1_TempCO2O2.csv
sensordashboard/audit-log.html
sensordashboard/create_temperature_table.sql
sensordashboard/dashboard_bridge.py
sensordashboard/domain-air.html
sensordashboard/domain-cooling.html
sensordashboard/domain-energy.html
sensordashboard/domain-fire.html
sensordashboard/domain-vaccine-raw.html
sensordashboard/domain-vaccine.html
sensordashboard/index.html
sensordashboard/settings.html
sensordashboard/shared.css
sensordashboard/temperature_event_generator.py
sensordashboard/temperature_subscriber.py
sensordashboard/temperature_uncertainty.py
sensordashboard/test/test_dashboard_bridge.py
sensordashboard/test/vaccine-data.test.js
sensordashboard/test_temperature_event_generator.py
sensordashboard/test_temperature_subscriber.py
sensordashboard/vaccine-analytics-prototype.js
sensordashboard/vaccine-bridge.js
sensordashboard/vaccine-data.js
sensordashboard/vaccine-raw.js
sensordashboard/vaccine.css
sensordashboard/vaccine.js
```

The CSV and legacy SQL have exact copies under `archive/`. The archive docs
and tests differ from their deleted originals. Several deleted HTML/CSS/JS
files have likely replacements under `web/`, but Git has not recognized these
as renames because the replacements are already committed at different paths
and the archive additions are still untracked.

## Workstream verification

| Workstream item | Local evidence | Status |
| --- | --- | --- |
| A: generator → listener flow | `services/temperature_event_generator.py`, `services/temperature_subscriber.py`, event contract tests, generator tests | Present locally but not pushed; current unit tests pass |
| A: PostgreSQL writer and two intentional projections | Atomic transaction in `temperature_subscriber.py`; `telemetry_logs` and `vaccine_temperature_events`; migration `004_add_run_id_correlation.sql` | Present locally but not pushed; current unit tests pass; DB integration skipped |
| A: read-only adapter, event/run correlation, latest-N verification | `services/dashboard_bridge.py`, `docs/database-access.md`, `database/verification/latest_events.sql`, HTTP/API tests | Present locally but not pushed; current unit tests pass; current sandbox skipped socket tests |
| A: health endpoints and 404 remediation | `/health`, `/ready`, `/api`, structured page-on-API-port 404 test | Present locally but not pushed; route test is currently skipped because localhost binding is restricted |
| B: daily/weekly/monthly/custom filters | `getDateRange` and browser tests | Present locally but not pushed; Node tests pass |
| B: timestamps/timezones, intervals, moving averages | `vaccine-data.js`, timezone and hourly aggregation tests | Present locally but not pushed; Node tests pass |
| B: latest-vs-average labels and CSV export | `summarizeSensors`, `buildExportPath`, dashboard page, browser/bridge tests | Present locally but not pushed; Node and Python tests pass |
| C: raw event display | `web/pages/domain-vaccine-raw.html`, `web/scripts/vaccine-raw.js` | Present locally but not pushed; present and referenced |
| C: configurable thresholds and warning/critical escalation | profile bounds, sensor uncertainty, `TEMPERATURE_BOUNDARY_RISK`, `VACCINE_SAFE_RANGE_VIOLATION` | Partially implemented; warning/critical verified, threshold state is not a dedicated stale/recovery state machine |
| C: stale detection | `domain_rules.py` has no `STALE` state or stale rule | Missing; no test |
| C: recovery state | `recovery` exists as a generator scenario/phase and UI trend label, but not as a persisted operational state | Partially implemented; no explicit rule/state-transition test |
| C: alert details/accessibility | alert markup, status labels, `aria` navigation assertions | Present locally but not pushed; browser tests pass for navigation/accessibility, not full alert state transitions |
| D: architecture/pipeline/data dictionary/runbook/troubleshooting | `sensordashboard/docs/` files listed above | Present locally but not pushed; final report confirms coverage |
| D: demo script and deterministic E2E | `docs/demo-script.md`, `scripts/e2e_verify.py`, `tests/e2e_scenarios.json`, `tests/test_e2e_assets.py` | Present locally but not pushed; prior report says 5/5 E2E passed, not rerun in this inventory phase |
| D: final verification reporting | untracked `docs/final-verification-report.md` | Present locally but not pushed; preserve before any synchronization |

## Test evidence and acceptance gates

Tests run during this phase without changing application files:

```text
PYTHONDONTWRITEBYTECODE=1 make test
46 Python tests passed; 5 skipped (localhost socket restrictions and DB integration guard)

node --test web/scripts/*.test.js
19 tests passed

node --check web/scripts/{vaccine,vaccine-data,vaccine-bridge,vaccine-inference,vaccine-inference-page,vaccine-navigation}.js
passed

AST parse of services/*.py, scripts/*.py, tests/*.py
27 files parsed successfully
```

The local final verification report records earlier evidence of 29 Node tests,
46/46 tests with database integration enabled, and 5/5 E2E cases. Those runs
are historical evidence, not a substitute for rerunning after reconciliation.

Before accepting any synchronization, run from the final reconciled project
root, in this order:

1. `make test` and all browser tests.
2. `RUN_DB_INTEGRATION=1 make test` with the intended local PostgreSQL schema.
3. `make verify-fast` and `make verify` against the same database.
4. `make e2e` with PostgreSQL and Mosquitto started by the documented setup.
5. A static website asset sweep, API health/readiness/404 check, and CSV export check.
6. A deterministic rule/state-transition test for warning, critical, stale, and recovery.
7. A clean-tree or staged-tree run proving that the generator’s archive CSV and
   every migration/documentation/test dependency are included in the proposed
   commit set.

## Required outcome before synchronization

### Must be committed and pushed after reconciliation

- The local `quant` remediation commits for Agents A, B, the completed portion
  of C, and D.
- The current `sensordashboard` source, database assets, tests, and docs as one
  coherent package.
- `sensordashboard/archive/data/Test1_TempCO2O2.csv`, because the current
  generator requires it at runtime.
- `sensordashboard/docs/final-verification-report.md`, after confirming it is
  the intended final report.
- `CONTEXT.md` and any approved domain ADR/spec files if they are intended to
  travel with the application repository.

### Must remain local and untracked/ignored

- `.venv/`, generated `models/`, `test-reports/`, Python bytecode, `.DS_Store`,
  Obsidian workspace/graph state, and other local environment metadata.
- The unrelated or not-yet-approved Internship learning artifacts, agent skill
  packs, personal documents, and home-directory files.
- Stitch upload/reference artifacts unless the repository owner explicitly
  wants them versioned.

### Conflicts that require an explicit decision

- Local `Documents/Internship/sensordashboard/` versus cached GitHub’s root
  `backend/`/`db/`/`frontend/`/`edge/`/`ai_worker/` handoff layout.
- Local current runbook port `8766` versus README port `8765`.
- Local source dependency on `archive/data/Test1_TempCO2O2.csv` versus the
  cached GitHub handoff’s intentionally removed large raw CSV.
- Local optional ML/inference work versus the unfinished baseline stale and
  explicit recovery-state requirement.
- The separate `Projects/iot_workspace/projects/temperature_iot_project` bridge
  and companion tree versus the maintained `sensordashboard` implementation.
- Whether the deleted flat files are intentional renames/archives or must be
  restored before a final commit.

No file in the local application candidate matched the private-key, common
cloud-key, GitHub-token, or obvious `password`/`secret`/`api_key` scan used in
this phase. Ignored environment files elsewhere in the home directory were
not treated as application deliverables and were not opened or modified.

