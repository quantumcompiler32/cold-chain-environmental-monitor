# Presentation update checklist

Use this checklist before sharing the dashboard, a screenshot, or the E2E
reports.

## Technical readiness

- [ ] `make e2e` passes.
- [ ] `test-reports/e2e-latest.json` and `test-reports/e2e-latest.md` were
      generated from the same run.
- [ ] `make test` passes.
- [ ] Browser data-layer tests pass with `node --test`.
- [ ] PostgreSQL and Mosquitto are local and reachable.
- [ ] The bridge `/health` response says `read_only: true`.
- [ ] The current scenario, seed, count, and batch correlation are recorded.

## Story and evidence

- [ ] The first slide explains the pipeline: generator → MQTT → listener →
      PostgreSQL → read-only bridge → dashboard.
- [ ] The data dictionary names `event_time`, `received_at`, and `stored_at`
      distinctly.
- [ ] At least one normal, warning, mixed/recovery, and outlier observation is
      shown or linked to the report.
- [ ] The presentation distinguishes raw temperature `status`, operational
      `severity`, and human disposition.
- [ ] The E2E report's run ID and case batch IDs are cited for the displayed
      evidence.

## Safety and wording

- [ ] Every synthetic chart or event is labelled `Demo simulation`.
- [ ] No slide says the prototype is live clinical monitoring.
- [ ] No slide says ML automatically releases, quarantines, or approves stock.
- [ ] ML model name, data basis, validation measure, and advisory limitation
      are visible when ML output is shown.
- [ ] Any missing service is shown as an explicit unavailable state, not filled
      with invented values.
- [ ] The reset command is not run against a shared or production database.

## Live handoff

- [ ] The presenter knows how to run `make demo-all COUNT=10` as a shorter
      fallback.
- [ ] The presenter knows how to open Operations, Raw Events, and
      Interpretation in that order.
- [ ] The latest JSON report is available for technical questions and the
      Markdown report is available for a human review.
