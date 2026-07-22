# Dashboard guide

This project is a local simulation. It helps compare generated readings and
does not make a vaccine release decision.

## What each visualization answers

| View | Useful question | Limitation |
| --- | --- | --- |
| Package temperature trend | Are the selected Pods moving together, drifting, or separating? | It shows generated/replayed data, not a physical refrigerator model. The y-axis focuses on the selected readings, so a far-away limit may be outside the plot. The range and target remain in the legend/profile strip. |
| Package health | How many Pods are currently stable, acceptable, too cold, or too warm? | It uses the latest reading for each Pod, so it does not show the duration of a problem. |
| Excursions and recovery | On which source days did the raw status leave the storage range? | This is a count of readings, not a validated alarm duration. |
| Scenario mix | Which scenario produced the data? | It describes the simulation label; it is not evidence that a real failure happened. |
| Scenario outcomes | Which scenarios create raw excursions and which create borderline uncertainty? | Scenarios are intentionally simple and deterministic. |
| Sensor variation | Which selected Pod has the widest minimum-to-maximum spread? | It summarizes the selected run; it does not estimate sensor drift or calibration quality. |
| Measurement uncertainty | How many readings have a possible +/-0.5 C interval that crosses a storage boundary? | The interval represents the paper's approximate Type-T accuracy. It is not a probability distribution. |
| Sensor table | What is the latest value, scenario, and reading count for each Pod? | Latest status is the original raw status. Borderline interpretation is shown in the uncertainty summary, not substituted into the raw status. |
| Raw events | What exact JSON fields arrived and in what order? | The page keeps the newest 80 visible rows and the bridge keeps a bounded history. |

## Running simulations

1. Start Mosquitto on `localhost:1883`.
2. From this folder, start the bridge: `python dashboard_bridge.py`.
3. Serve the folder: `python3 -m http.server 8765`.
4. Open `http://127.0.0.1:8765/index.html` and select Vaccine Cold Chain.
5. Open **Live runner** at the top.
6. Choose Pods, one or more scenarios, interval, and events per scenario per Pod.
7. Press **Start live run**. Press **Stop** at any time.

The total requested event count is:

```text
selected Pods × selected scenarios × events per scenario per Pod
```

Each Pod/scenario combination has its own bounded generator process. The
bridge subscribes once to MQTT, gives every received event a unique sequence,
and sends it to Analytics and Raw events. The charts update while the run is
active. Raw events has **Auto-scroll newest** enabled by default.

## Replaying an uploaded CSV

On Live runner, choose a CSV and press **Upload CSV for replay**. The bridge
stores it temporarily for the next run. The CSV must contain `date`, `time`,
and the selected `Pod1`-`Pod20` column. Pod values are interpreted as
Fahrenheit, matching the bundled experiment. The uploaded file is not added to
Git and is deleted when the bridge stops.

## Temperature uncertainty

The paper documents approximately `+/-0.5 C` accuracy for the Type-T
thermocouples used by the dataset. The dashboard stores the raw measured value
in `temperature_c` unchanged and adds:

- `sensor_tolerance_c`
- `temperature_min_possible_c`
- `temperature_max_possible_c`
- `uncertainty_status`
- `boundary_crossing`
- `measurement_confidence`

The original rules remain the raw `status` rules:

- below `-80 C`: `TOO_COLD`
- `-80 C` through `-60 C`: `ACCEPTABLE`
- within `1 C` of `-78.5 C`: `STABLE`
- above `-60 C`: `TOO_WARM`

For Moderna, the runner starts with suggested frozen bounds of `-50 C` to
`-15 C`, matching [Moderna's Spikevax storage guidance](https://products.modernatx.com/spikevaxpro/dosing-and-administration). These bounds appear only after selecting Moderna and can be changed for a simulation.

Uncertainty is a second interpretation:

- `-80.2 C` has a possible range of `-80.7 C` to `-79.7 C`, so it is `BORDERLINE_COLD`.
- `-79.8 C` has a possible range of `-80.3 C` to `-79.3 C`, so it is also `BORDERLINE_COLD`.
- `-81.0 C` has a possible range of `-81.5 C` to `-80.5 C`, so it is `CLEARLY_TOO_COLD`.

Sensor accuracy is measurement uncertainty. Vaccine storage tolerance is the
acceptable storage range. They are not the same value.

## Scenarios

- **Normal**: source variation around the selected profile target.
- **Outlier**: normal variation with an intentional cold or warm exception on every twentieth event.
- **Failure**: every event is above the selected maximum.
- **Recovery**: starts above the selected maximum and moves toward the target.

Scenarios can run together. The scenario label stays on every event, so the
scenario charts can compare them.

## Known limits

- Mosquitto and the bridge are local services with no authentication.
- PostgreSQL saving is optional and requires the migrated `temperature_events` table.
- The source CSV is replayed; it does not model thermal inertia, packaging, transport delay, sensor drift, or a validated alarm policy.
- The bridge history is bounded and Raw events displays only the newest 80 rows.
- The default bundled CSV is an ultralow experiment. A Moderna run shifts source variation around the selected Moderna target; it is still a simulation.
