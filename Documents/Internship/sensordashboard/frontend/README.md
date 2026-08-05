# Frontend

The browser-only dashboard lives here. `index.html` is the landing page;
`pages/` contains the dashboard views, `scripts/` contains read-only API and
analytics clients, `styles/` contains CSS, and `tests/` contains Node tests for
filters, CSV export, timestamps, aggregation, and navigation.

Serve this directory from the project root with:

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend
```
