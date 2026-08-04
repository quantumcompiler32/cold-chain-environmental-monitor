# Demo script

Use the following five-minute script. Say “synthetic demo simulation” before
showing the first event; do not describe the output as live clinical telemetry
or an automated vaccine release decision.

## Before the audience arrives

1. Start PostgreSQL and Mosquitto.
2. Start the listener, dashboard bridge, website, and optional ML service.
3. Run `make e2e` and keep both report files as evidence.
4. Open the Operations page with all Pods selected.

## Talk track and commands

### 1. Establish the baseline

“The system separates event creation, transport, persistence, and display. The
dashboard is reading committed local PostgreSQL rows through a read-only
bridge.”

```bash
make run-scenario SENSORS=Pod1 SCENARIO=normal COUNT=6 INTERVAL_MS=150 SEED=101
```

Point out a `NORMAL` Pod and the explicit `event_time`, `received_at`, and
`stored_at` lifecycle timestamps.

### 2. Show a review-worthy boundary

“A warning can be useful before a hard out-of-range status. This case stays in
the selected range, but the sensor uncertainty interval reaches the boundary.”

```bash
make run-scenario SENSORS=Pod2 SCENARIO=warning COUNT=6 INTERVAL_MS=150 SEED=102
```

Point out `TEMPERATURE_BOUNDARY_RISK` and the distinction between raw
temperature `status` and derived `operational_status`.

### 3. Show a failure and recovery sequence

“The mixed scenario keeps one top-level scenario for the run and labels the
normal, cooling-failure, and recovery phases separately.”

```bash
make run-scenario SENSORS=Pod3 SCENARIO=mixed COUNT=9 INTERVAL_MS=250 SEED=104
```

Point out the exception-first attention state, then the recovery trend. Do not
claim that recovery alone released affected stock.

### 4. Show raw evidence and correlation

Open the Raw Events page, then query the bridge:

```bash
curl -sS 'http://127.0.0.1:8787/api/verification/latest-events'
curl -sS 'http://127.0.0.1:8787/api/analytics?scenario=mixed'
```

Explain that the E2E report uses the same public API with a unique `batch_id`,
so its counts cannot be confused with old demo rows.

### 5. Close with the ML boundary

“The Interpretation tab is advisory model context. It is separately started,
loads saved artifacts, and cannot write events or make stock disposition
decisions.”

If the service is ready, submit one event in the Interpretation tab. If it is
not ready, show the explicit unavailable state; the operational dashboard is
still valid without ML.

## Presenter checks

- Keep the `Demo simulation` label visible.
- Prefer `make e2e` report evidence over screenshots of invented values.
- Say which scenario is running before each command.
- Call out one operator action: inspect the exception, review affected stock,
  and record disposition separately.
