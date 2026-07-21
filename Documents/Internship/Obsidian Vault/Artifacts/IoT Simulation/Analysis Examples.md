# Analysis Examples

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Read the CSV

```python
import pandas as pd

df = pd.read_csv("telemetry.csv", parse_dates=["timestamp"])
df = df.sort_values("timestamp")
```

## Inspect data quality

```python
print(df.head())
print(df.dtypes)
print(df.isna().sum())
```

## Readings by device

```python
summary = (
    df.groupby("device_id")
      .agg(
          readings=("id", "count"),
          average_temperature=("temperature", "mean"),
          average_humidity=("humidity", "mean"),
          average_pressure=("pressure", "mean"),
      )
)
print(summary)
```

## Temperature chart

```python
import matplotlib.pyplot as plt

for device_id, group in df.groupby("device_id"):
    plt.figure(figsize=(10, 4))
    plt.plot(group["timestamp"], group["temperature"], marker="o")
    plt.title(f"Temperature — {device_id}")
    plt.xlabel("Time")
    plt.ylabel("Temperature")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
```

## Local automated version

```bash
iot analyze
```

---

Related: [[Analytics Overview]]
