# Vaccine cold-chain dashboard

Open `index.html` and select **Vaccine Cold Chain**. The page is labelled `DEMO SIMULATION` so it is clear that this is a UI prototype, not a live clinical monitoring system or an automatic vaccine release decision.

## What is included

- Pfizer ultralow profile: target `−78.5°C`, acceptable range `−80°C` to `−60°C`.
- All `Pod1`–`Pod20` package sensors in the overview.
- A readable fixed-scale trend chart with sensor selection.
- Temperature, status, excursion/recovery, scenario, and replay-provenance visualizations.
- Dedicated raw-event page with a sensor filter and readable JSON event text.
- Dedicated live-runner page; the run length is fixed at 20 events per selected Pod so Pod selection stays the only device choice.
- Local CSV/JSON loading for `temperature_events_export.csv`, the wide `Test1_TempCO2O2.csv` experiment file, or JSON temperature events.
- CSV export for the sensors currently selected in the trend chart.
- Simulation-focused alerts that explain generated out-of-range behavior without clinical review actions.

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

The browser pages use a local API/MQTT adapter for optional live runs. Analytics stays focused on visualizations, while `domain-vaccine-live.html` owns the controls and `domain-vaccine-raw.html` owns imports/raw event text. The pages deliberately do not connect directly to PostgreSQL or make a clinical disposition automatically.

## Live event runner

Start Mosquitto, then run the bridge beside the temperature generator:

```bash
cd /Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project
./.venv/bin/python dashboard_bridge.py
```

Open the dashboard through the normal local web server and wait for **Bridge connected**. For example:

```bash
cd /Users/mokshjoshi/Documents/Internship/sensordashboard
python3 -m http.server 8765
```

Then open `http://127.0.0.1:8765/index.html`, open **Vaccine Cold Chain**, and use the **Live runner** link. Choose several Pods, a profile, and a scenario, then press **Start live run**. The analytics page clears its current view and redraws every graph and KPI as MQTT messages arrive; the raw page shows the same events as readable JSON. The Moderna / Spikevax frozen-storage suggestion is −50°C to −15°C, sourced from [Moderna’s storage guidance](https://products.modernatx.com/spikevaxpro/dosing-and-administration), and remains editable for simulation experiments. PostgreSQL saving is optional and should only be enabled when the existing `temperature_events` table is available.

## Verification

From `/Users/mokshjoshi/Documents/Internship`:

```bash
node --test sensordashboard/test/vaccine-data.test.js
/Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project/.venv/bin/python -m unittest sensordashboard/test/test_dashboard_bridge.py
```

The test seam covers profile threshold classification, CSV event parsing, sensor summaries, repeated live timestamps, bridge request validation, generator commands, and MQTT-to-subscriber event enrichment. `index.html` and `shared.css` are copied unchanged from the supplied dashboard shell.
