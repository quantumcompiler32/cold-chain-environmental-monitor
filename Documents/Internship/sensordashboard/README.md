# Vaccine cold-chain dashboard

Open `index.html` and select **Vaccine Cold Chain**. The page is labelled `DEMO SIMULATION` so it is clear that this is a UI prototype, not a live clinical monitoring system or an automatic vaccine release decision.

## What is included

- Pfizer ultralow profile: target `−78.5°C`, acceptable range `−80°C` to `−60°C`.
- All `Pod1`–`Pod20` package sensors in the overview.
- A readable focused-axis trend chart with sensor selection.
- A focused trend axis that makes small line variation visible without changing the stored values.
- Temperature, status, excursion/recovery, scenario, and replay-provenance visualizations.
- Dedicated raw-event page with a sensor filter and readable JSON event text.
- Dedicated live-runner page with variable events per Pod/scenario, multiple scenarios in one run, Stop at any time, and CSV upload for the next replay.
- Local CSV/JSON loading for `temperature_events_export.csv`, the wide `Test1_TempCO2O2.csv` experiment file, or JSON temperature events.
- CSV export for the sensors currently selected in the trend chart.
- Simulation-focused alerts that explain generated out-of-range behavior without clinical review actions.
- [SCENARIOS.md](SCENARIOS.md), which explains each scenario, profile bounds, data flow, and limitations.
- [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md), which explains what each visualization answers and its limitation.

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
  "status": "STABLE",
  "sensor_tolerance_c": 0.5,
  "temperature_min_possible_c": -78.9,
  "temperature_max_possible_c": -77.9,
  "uncertainty_status": "WITHIN_RANGE"
}
```

The dashboard starts with deterministic built-in demo events so it works when `index.html` is opened directly. The demo includes an active too-cold Pod and an active too-warm Pod so the dashboard does not falsely present an all-clear state. Use **Load CSV / JSON** to load a file from the temperature IoT project. The importer accepts both the event-shaped export and the experiment's wide `date,time,Pod1,…` format, converts the experiment's Fahrenheit Pod values to Celsius, and samples very large files to keep the browser responsive. The data adapter in `vaccine-data.js` derives the status from the documented Pfizer profile rather than trusting a stale status field.

The browser pages use a local API/MQTT adapter for optional live runs. Analytics stays focused on visualizations, while `domain-vaccine-live.html` owns the controls and `domain-vaccine-raw.html` owns imports/raw event text. The pages deliberately do not connect directly to PostgreSQL or make a clinical disposition automatically. See [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) for the purpose and limit of each chart.

## Live event runner

Start Mosquitto, then run the bridge from this same folder as the dashboard:

```bash
cd /path/to/sensordashboard
source .venv/bin/activate
python dashboard_bridge.py
```

Open the dashboard through the normal local web server and wait for **Bridge connected**. For example:

```bash
cd /path/to/sensordashboard
python3 -m http.server 8765
```

Then open `http://127.0.0.1:8765/index.html`, open **Vaccine Cold Chain**, and use the top switcher. Choose several Pods, a profile, and a scenario in **Live runner**, then press **Start live run**. The Analytics page clears its current view, locks its trend to the run-selected Pods, and redraws every graph and KPI as MQTT messages arrive; the Raw events page shows the same events as readable JSON. The Moderna / Spikevax frozen-storage suggestion is −50°C to −15°C, sourced from [Moderna’s storage guidance](https://products.modernatx.com/spikevaxpro/dosing-and-administration), and remains editable for simulation experiments. PostgreSQL saving is optional and should only be enabled when the existing `temperature_events` table is available.

## Verification

From the dashboard folder:

```bash
node --test test/vaccine-data.test.js
python -m unittest discover -s test -p 'test*.py'
python -m unittest test_temperature_event_generator.py test_temperature_subscriber.py test_analyze_temperature_database.py
```

The test seam covers profile threshold classification, CSV event parsing, sensor summaries, repeated live timestamps, bridge request validation, generator commands, scenario behavior, and MQTT-to-subscriber event enrichment. `index.html` and `shared.css` are copied unchanged from the supplied dashboard shell. All bridge, generator, data, schema, and Python test files needed for this demo are together in this folder.
