# 2026-07-20 — MQTT PostgreSQL And Event Pipeline

## Goals

- Verify Mosquitto and PostgreSQL.
- Use the refrigeration CSV as the event source.
- Run the event generator, MQTT subscriber, and database listener together.
- Generate JSON events at a configurable interval and persist them.

## Completed

- Verified Mosquitto and PostgreSQL were running.
- Confirmed the CSV contained the full dataset.
- Confirmed the Python environment and required packages.
- Successfully ran the subscriber, listener, and event generator together.
- Confirmed the subscriber displayed events and the listener wrote the same events into PostgreSQL.
- Created shortcuts for running the project components.

## Feedback and artifacts

Venkat asked for the custom event-generator prompt, generated Python code, and JSON format. Moksh replied with `temperature_event_generator.py`, `sample_temperature_event.json`, and `Project File Prompt.md`, explaining that the generator used the original `Arduino_events_simulate.py` as a reference and `Test1_TempCO2O2.csv` as its real-reading source.

## Next

- Finish the dataset description, data dictionary, ranges, and outliers.
- Confirm JSON-to-SQL field alignment.
- Build the PostgreSQL analytics program.

## Related notes

- [[ByteSmart Project]]
- [[Current Internship Work Queue]]
- [[Bitwise Internship Timeline]]

