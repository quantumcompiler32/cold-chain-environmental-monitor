# End-to-end verification

Workstream D's single automated command is:

```bash
cd "$(git rev-parse --show-toplevel)"
make e2e
```

The command starts a temporary MQTT listener and dashboard bridge, invokes the
existing generator CLI for every case in
[tests/e2e_scenarios.json](../tests/e2e_scenarios.json), and reads events back
through `GET /api/events?batch=...`. The test does not import temperature
transformation functions or call persistence internals. Its assertions are
observable contracts: event count, correlation key, scenario/phase labels,
operational status, alert, and the expected first/last status where relevant.

Each invocation creates a unique run ID and passes it through the public
generator interface. Each scenario receives a batch ID of `<run-id>-<scenario>`.
This gives the report a stable join key across:

```text
generator summary → batch_id → persisted bridge response → report case
```

The command does not reset or delete database rows. It requires the local
services and the canonical schema to already exist. If it fails, inspect the
service logs and the report files before rerunning.

## Report contract

The machine-readable report is `test-reports/e2e-latest.json`:

- `run_id`, timestamps, environment, and bridge URL identify the run;
- `cases[]` records each command, batch ID, generator summary, API status,
  observed count, and named checks;
- `summary.status` is `passed` only when every manifest case passes;
- `service_logs` and `errors` preserve failure evidence without secrets.

The human-readable report is `test-reports/e2e-latest.md`. Generated reports
are ignored by Git so timestamps and local host details are not committed.
