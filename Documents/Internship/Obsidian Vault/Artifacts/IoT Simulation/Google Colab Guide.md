# Google Colab Guide

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Open Colab and prepare the data

```bash
iot upload
```

## Use the included notebook

Upload this file to Google Colab:

```text
notebooks/IoT_Telemetry_Analysis.ipynb
```

Then run the cells from top to bottom.

## Minimal Colab code

```python
from google.colab import files
import io
import pandas as pd
import matplotlib.pyplot as plt

uploaded = files.upload()
filename = next(iter(uploaded))
df = pd.read_csv(io.BytesIO(uploaded[filename]), parse_dates=["timestamp"])
df = df.sort_values("timestamp")

display(df.head())
display(df.isna().sum().to_frame("missing_values"))
display(df.groupby("device_id").size().to_frame("readings"))
```

## Missing data expectation

The DHT22 device has humidity but no pressure. The BMP280 device has pressure but no humidity. Pandas should represent missing sensor values as `NaN`; this is expected and should not cause rows to be dropped automatically.

## Visualization milestone

Create:

- Temperature over time.
- Humidity over time for DHT22.
- Pressure over time for BMP280.
- A dual-axis temperature and pressure chart.

---

Related: [[Analytics Overview]] · [[Analysis Examples]]
