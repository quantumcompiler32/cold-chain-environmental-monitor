# Phase 1 local integrated prototype

This is the isolated local UI update for the three non-Impact Stitch screens:
Operations, Raw Events, and Interpretation/Methodology. It does not replace or
modify the baseline dashboard.

## Run locally

From `sensordashboard/`, start the read-only bridge when PostgreSQL is
available. Use the first command in the reorganized local worktree, or the
second command in a clean baseline checkout:

```bash
python3 services/dashboard_bridge.py
python3 dashboard_bridge.py
```

In another terminal, serve the local UI:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

Open <http://127.0.0.1:8765/phase1-stitch-ui/>.

If the bridge is offline, the UI remains usable for layout review and shows
explicit offline and insufficient-data states instead of placeholder readings.

## Tests

```bash
node --test phase1-stitch-ui/*.test.js
```

The local analysis is limited to linear regression, logistic regression, and
k-means clustering. Results identify their data basis and validation metric;
they never make stock disposition decisions.
