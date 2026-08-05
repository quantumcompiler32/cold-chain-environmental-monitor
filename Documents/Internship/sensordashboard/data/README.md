# Source data

`Test1_TempCO2O2.csv` is a bundled synthetic/source-variation fixture used by
the event generator and optional model-training command.

It is not a historical event store. The generator converts its Fahrenheit Pod
readings to Celsius, applies the selected scenario, and assigns a new current
UTC `event_time` to every generated event. PostgreSQL is the source of truth
for persisted events.
