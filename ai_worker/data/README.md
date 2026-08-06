# Source data

`Test1_TempCO2O2.csv` is the canonical local copy of the Test 1 CSV used by
the provided Colab-derived analysis, optional model-training command, and
event generator.

It is not a historical event store. The generator converts its Fahrenheit Pod
readings to Celsius, applies the selected scenario, and assigns a new current
UTC `event_time` to every generated event. PostgreSQL is the source of truth
for persisted events. The CSV is an ultralow-temperature refrigeration
experiment dataset, not a GARDASIL 9 pharmacy-refrigerator dataset.
