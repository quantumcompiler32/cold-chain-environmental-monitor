# Vaccine cold-chain dashboard

Open `index.html` and select **Vaccine Cold Chain**. The page is labelled `DEMO SIMULATION` so it is clear that this is a UI prototype, not a live clinical monitoring system or an automatic vaccine release decision.

## What is included

- Pfizer ultralow profile: target `−78.5°C`, acceptable range `−80°C` to `−60°C`.
- All `Pod1`–`Pod20` package sensors in the overview.
- A readable six-sensor default trend chart with sensor selection.
- Temperature, status, excursion/recovery, scenario, and replay-provenance visualizations.
- Raw event stream with a sensor filter.
- Local CSV/JSON loading for `temperature_events_export.csv`, the wide `Test1_TempCO2O2.csv` experiment file, or JSON temperature events.
- CSV export for the sensors currently selected in the trend chart.
- Clear “review excursion” and “view trend” actions.

## Data flow

The page uses the same event vocabulary as the temperature IoT project:

```json
{
  "device_id": "vaccine_temperature_simulator",
  "timestamp": "2026-07-22T10:15:00Z",
  "source_timestamp": "2020-12-16T11:26:43Z",
  "sensor_name": "Pod1",
  "vaccine_type": "pfizer_ultralow",
  "scenario": "normal",
  "temperature_c": -78.4,
  "status": "STABLE"
}
```

The dashboard starts with deterministic built-in demo events so it works when `index.html` is opened directly. The demo includes an active too-cold Pod and an active too-warm Pod so the dashboard does not falsely present an all-clear state. Use **Load CSV / JSON** to load a file from the temperature IoT project. The importer accepts both the event-shaped export and the experiment's wide `date,time,Pod1,…` format, converts the experiment's Fahrenheit Pod values to Celsius, and samples very large files to keep the browser responsive. The data adapter in `vaccine-data.js` derives the status from the documented Pfizer profile rather than trusting a stale status field.

The browser page is ready for a future API/MQTT adapter. It deliberately does not connect directly to PostgreSQL or make a clinical disposition automatically.

## Verification

From the repository root:

```bash
node --test sensordashboard/test/vaccine-data.test.js
```

The test seam covers Pfizer threshold classification, CSV event parsing, sensor summaries, and selectable chart series. `index.html` and `shared.css` are copied unchanged from the supplied dashboard shell.
