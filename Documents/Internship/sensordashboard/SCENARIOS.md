# Vaccine dashboard scenarios and limitations

This dashboard is a local simulation and visualization tool. It is useful for
demonstrating the MQTT-to-dashboard data flow, testing chart behavior, and
showing how temperature classifications change. It is not a validated cold
chain monitoring system and it must not be used to release, quarantine, or
discard vaccine inventory.

## Scenarios

Choose a scenario in **Live runner**, choose one or more Pods, and start the
bounded run. Every selected Pod emits 20 events. The same scenario is applied
independently to each selected Pod.

| Scenario | What it does | What to expect |
| --- | --- | --- |
| `normal` | Replays the source pattern without adding an excursion. | The graph shows ordinary variation around the selected vaccine profile target. |
| `outlier` | Preserves the source pattern, then makes the final event an intentional out-of-range reading. | Each selected Pod produces one visible exception in a 20-event run. |
| `failure` | Holds every generated event above the selected maximum. | The health summary and warm excursion counts remain abnormal for the run. |
| `recovery` | Starts above the selected maximum and moves linearly toward the profile target. | The trend should move toward stability as events arrive. |

The runner creates one generator process per selected Pod. This makes each
Pod's stream independent while the bridge subscribes only once to MQTT. The
Analytics page uses the exact Pod list stored in the run status, so its trend
does not silently switch to a different set of Pods. The Pod chips on
Analytics are intentionally locked during a live run; they are a display of
the run selection, not a second control.

## Profiles and temperature bounds

- **Pfizer ultralow** uses a simulation target of `−78.5°C` and a fixed
  simulation range of `−80°C` to `−60°C`.
- **Moderna / Spikevax** uses a simulation target of `−32.5°C`. When Moderna
  is selected, the runner shows editable suggested frozen-storage bounds of
  `−50°C` to `−15°C`. Those fields are hidden for Pfizer and are sent to the
  bridge only for Moderna.

The Moderna suggestion is based on the manufacturer’s storage guidance. The
official page describes frozen storage at `−50°C` to `−15°C`; it also describes
post-thaw conditions, which are outside this frozen-storage simulation:
[Moderna Spikevax dosing and administration](https://products.modernatx.com/spikevaxpro/dosing-and-administration).
The dashboard displays a link to that source when Moderna is active. These
values are simulation defaults, not a clinical release rule.

The bundled source CSV contains a Pfizer ultralow experiment. For a Moderna
`normal` run, the generator preserves each source variation but shifts its
baseline around the Moderna target. This avoids making every normal Moderna
event look like an accidental Pfizer-temperature excursion.

## Data flow

1. The browser sends the selected profile, scenario, Pods, interval, bounds,
   and database toggle to `dashboard_bridge.py`.
2. The bridge validates the request and starts one bounded
   `temperature_event_generator.py` process per Pod.
3. Each generator publishes a JSON temperature event to
   `devices/temperature` through the local Mosquitto broker.
4. The bridge receives the event once, adds a unique sequence and `run_id`,
   then forwards it to open pages through Server-Sent Events. Browser polling
   remains available as a fallback.
5. Analytics batches redraws with `requestAnimationFrame`; Raw events keeps
   only the newest 80 visible rows while retaining a bounded in-memory event
   history.

## Limitations

- Mosquitto must be running at `localhost:1883` for live MQTT runs.
- The bridge is intentionally local-only and has no authentication. Do not
  expose it to a network or use it with sensitive production data.
- The generator replays a CSV experiment; it does not model a physical
  refrigerator, packaging, thermal inertia, sensor drift, calibration error,
  transport delay, or a validated alarm policy.
- A run is bounded to 20 events per selected Pod. The interval controls pacing,
  not the number of events. This keeps demonstrations short and prevents a
  forgotten simulation from running forever.
- `outlier` produces one clear outlier per Pod with the current 20-event
  default. Longer command-line runs can produce additional alternating cold
  and warm outliers.
- `failure` is deliberately simple and always warm; it is not a realistic
  failure model.
- `recovery` is a straight-line interpolation to the target, not a physical
  recovery curve.
- The optional PostgreSQL toggle requires the local `iotdb` database and the
  `temperature_events` table created by `create_temperature_table.sql`.
- CSV/JSON imports are parsed in the browser. Very large files are sampled or
  capped to keep the page responsive, and imported status values are derived
  from the active profile.
- The visualizations are simulation analytics only. Excursions explain the
  generated behavior; they are not approval or disposition recommendations.

## GitHub-ready local setup

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python dashboard_bridge.py
```

In a second terminal, serve the static dashboard:

```bash
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/index.html`, choose **Vaccine Cold Chain**, and
use the top dashboard switcher to move between Analytics, Live runner, and Raw
events. The `.gitignore` excludes the local virtual environment and Python
cache files; the source CSV and schema remain beside the scripts so the folder
can be uploaded as one project.
