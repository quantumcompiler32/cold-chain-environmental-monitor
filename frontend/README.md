# Frontend

The browser-only dashboard lives here. `index.html` is the landing page;
`pages/` contains the dashboard views, `scripts/` contains read-only API and
analytics clients, and `styles/` contains CSS. The maintained vaccine pages
read committed events through the backend dashboard bridge.

Serve this directory from the project root with:

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend
```

## File guide

| File | Purpose |
|---|---|
| `index.html` | Landing page for the dashboard. |
| `pages/domain-vaccine.html` | Main vaccine analytics dashboard. |
| `pages/domain-vaccine-raw.html` | Read-only persisted event log. |
| `pages/domain-vaccine-inference.html` | Optional advisory ML inference page. |
| `pages/domain-cooling.html` | Cooling-domain visual prototype. |
| `pages/domain-energy.html` | Energy-domain visual prototype. |
| `pages/domain-air.html` | Air-quality domain visual prototype. |
| `pages/domain-fire.html` | Fire-risk domain visual prototype. |
| `pages/audit-log.html` | Audit-log interface prototype. |
| `pages/settings.html` | Dashboard settings interface. |
| `scripts/vaccine-bridge.js` | Calls the dashboard API and listens for live SSE events. |
| `scripts/vaccine-data.js` | Normalizes events and performs frontend calculations. |
| `scripts/vaccine.js` | Renders vaccine analytics, charts, filters, and Pod details. |
| `scripts/vaccine-raw.js` | Renders raw persisted events and live updates. |
| `scripts/vaccine-inference.js` | Builds requests to the optional ML service. |
| `scripts/vaccine-inference-page.js` | Controls the inference page and displays model results. |
| `scripts/vaccine-navigation.js` | Creates shared vaccine-page navigation. |
| `styles/shared.css` | Shared layout and dashboard styling. |
| `styles/vaccine.css` | Vaccine dashboard styling. |
| `styles/vaccine-monitoring.css` | Monitoring cards, alerts, charts, and event-row styling. |
| `styles/phase1-shell-skin.css` | Application shell theme. |
| `styles/phase1-vaccine-skin.css` | Vaccine-page visual theme. |
| `favicon.svg` | Browser tab icon. |
