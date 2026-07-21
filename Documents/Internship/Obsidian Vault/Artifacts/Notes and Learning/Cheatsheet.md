# IoT Simulator → MQTT → PostgreSQL → CSV → Google Colab Cheatsheet

> Goal: Generate simulated IoT telemetry events, stream them through Mosquitto MQTT, listen with Python, insert into PostgreSQL, export to CSV, and analyze in Google Colab using `numpy`, `pandas`, and `matplotlib`.

---

## 0. System Overview

```text
Simulator / Publisher
        |
        | MQTT publish
        v
Mosquitto Broker
Topic: telemetry
        |
        | MQTT subscribe
        v
Listener / Subscriber
        |
        | INSERT rows
        v
PostgreSQL
Database: iot_simulation
Table: telemetry_logs
        |
        | COPY export
        v
CSV File
        |
        | Upload
        v
Google Colab Analysis
```

### Data Flow

| Step | Component | Purpose |
|---|---|---|
| 1 | Simulator / Publisher | Generates temperature, humidity, and pressure data |
| 2 | Mosquitto | MQTT broker that receives and distributes messages |
| 3 | Listener / Subscriber | Reads MQTT messages and inserts them into PostgreSQL |
| 4 | PostgreSQL | Stores telemetry records in `telemetry_logs` |
| 5 | CSV Export | Dumps database records into a `.csv` file |
| 6 | Google Colab | Loads CSV and analyzes data with Python |

---

# Terminal Setup Summary

You will usually need **4 terminals open**:

| Terminal | Purpose |
|---|---|
| Terminal 1 | Run Mosquitto MQTT broker |
| Terminal 2 | Run PostgreSQL commands / database checks |
| Terminal 3 | Run the simulator / publisher |
| Terminal 4 | Run the listener / subscriber |

Optional:

| Terminal | Purpose |
|---|---|
| Terminal 5 | Export CSV / run analysis scripts locally |
| Google Colab | Upload CSV and analyze data |

---

# 1. Project Folder Layout

Recommended structure:

```text
iot-mqtt-postgres-project/
│
├── simulator/
│   └── publisher.py
│
├── listener/
│   └── subscriber.py
│
├── analysis/
│   ├── iot_data_analysis.py
│   └── exported_telemetry.csv
│
├── requirements.txt
└── README.md
```

### What This Means

| Folder/File | Purpose |
|---|---|
| `simulator/publisher.py` | Generates sensor data and publishes it to MQTT |
| `listener/subscriber.py` | Subscribes to MQTT and inserts data into PostgreSQL |
| `analysis/iot_data_analysis.py` | Loads CSV and performs custom analysis |
| `requirements.txt` | Python dependencies |
| `exported_telemetry.csv` | Exported data from PostgreSQL |

---

# 2. Terminal 1 — Start Mosquitto MQTT Broker

## Option A — macOS Homebrew

```bash
brew services start mosquitto
```

### What it does

Starts Mosquitto as a background service.

### Verify Mosquitto is running

```bash
brew services list
```

Look for:

```text
mosquitto started
```

---

## Option B — Run Mosquitto in Foreground

```bash
mosquitto -v
```

### What it does

Runs Mosquitto broker in verbose mode so you can see connections and messages.

### Expected output

```text
mosquitto version x.x.x starting
Opening ipv4 listen socket on port 1883
```

---

## Option C — Windows

Open PowerShell or Command Prompt:

```powershell
net start mosquitto
```

Or run directly from install directory:

```powershell
mosquitto -v
```

---

# 3. Terminal 2 — PostgreSQL Setup

## Start PostgreSQL

### macOS Homebrew

```bash
brew services start postgresql
```

or, depending on your installed version:

```bash
brew services start postgresql@16
```

### Verify PostgreSQL is running

```bash
brew services list
```

---

## Enter PostgreSQL Shell

```bash
psql postgres
```

or:

```bash
psql -U postgres
```

### What it does

Opens the PostgreSQL command shell so you can create databases, tables, and run SQL.

---

# 4. Create the Database

Inside `psql`:

```sql
CREATE DATABASE iot_simulation;
```

### What it does

Creates a database named `iot_simulation`.

---

## Connect to the Database

```sql
\c iot_simulation
```

### What it does

Switches from the default database into your IoT simulation database.

---

# 5. Create the Telemetry Table

Inside `psql`, run:

```sql
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id SERIAL PRIMARY KEY,
    temperature DOUBLE PRECISION NOT NULL,
    humidity DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION NOT NULL,
    topic TEXT DEFAULT 'telemetry',
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### What each column means

| Column | Meaning |
|---|---|
| `id` | Auto-generated row ID |
| `temperature` | Simulated temperature value |
| `humidity` | Simulated humidity value |
| `pressure` | Simulated pressure value |
| `topic` | MQTT topic name, defaulting to `telemetry` |
| `received_at` | Timestamp when row was inserted |

---

## Verify Table Exists

```sql
\dt
```

Expected result:

```text
public | telemetry_logs | table
```

---

## View Table Structure

```sql
\d telemetry_logs
```

---

# 6. Python Virtual Environment Setup

From your project root:

```bash
cd iot-mqtt-postgres-project
```

## Create virtual environment

```bash
python3 -m venv .venv
```

### What it does

Creates an isolated Python environment inside `.venv`.

---

## Activate virtual environment

### macOS / Linux

```bash
source .venv/bin/activate
```

---

## Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## Install dependencies

```bash
pip install paho-mqtt psycopg2-binary pandas numpy matplotlib
```

### What each package does

| Package | Purpose |
|---|---|
| `paho-mqtt` | Python MQTT client |
| `psycopg2-binary` | PostgreSQL database driver |
| `pandas` | Data loading and analysis |
| `numpy` | Numerical calculations |
| `matplotlib` | Charts and visualization |

---

## Save dependencies

```bash
pip freeze > requirements.txt
```

---

## Reinstall dependencies later

```bash
pip install -r requirements.txt
```

---

# 7. Terminal 3 — Run Simulator / Publisher

Go to your project folder:

```bash
cd iot-mqtt-postgres-project
source .venv/bin/activate
```

Run publisher:

```bash
python simulator/publisher.py
```

### What it does

The simulator should:

1. Generate fake telemetry data.
2. Include temperature, humidity, and pressure.
3. Publish the data to Mosquitto.
4. Send messages to the MQTT topic:

```text
telemetry
```

### Expected output example

```text
Published: {"temperature": 72.5, "humidity": 44.2, "pressure": 1012.8}
Published: {"temperature": 73.1, "humidity": 45.0, "pressure": 1012.6}
```

---

# 8. Terminal 4 — Run Listener / Subscriber

Open another terminal:

```bash
cd iot-mqtt-postgres-project
source .venv/bin/activate
```

Run subscriber:

```bash
python listener/subscriber.py
```

### What it does

The listener should:

1. Connect to Mosquitto.
2. Subscribe to the `telemetry` topic.
3. Read incoming JSON messages.
4. Format the data.
5. Insert rows into PostgreSQL:

```text
Database: iot_simulation
Table: telemetry_logs
```

### Expected output example

```text
Connected to MQTT broker
Subscribed to topic: telemetry
Inserted row: temperature=72.5, humidity=44.2, pressure=1012.8
```

---

# 9. Manual MQTT Testing

Use this if you want to verify Mosquitto works before running Python.

## Terminal A — Subscribe to telemetry topic

```bash
mosquitto_sub -h localhost -t telemetry
```

### What it does

Listens for messages published to the `telemetry` topic.

---

## Terminal B — Publish test message

```bash
mosquitto_pub -h localhost -t telemetry -m '{"temperature":72.5,"humidity":44.2,"pressure":1012.8}'
```

### What it does

Sends one test JSON message to the MQTT broker.

### Expected result

The subscriber terminal should print:

```json
{"temperature":72.5,"humidity":44.2,"pressure":1012.8}
```

---

# 10. Verify Data Reached PostgreSQL

Open PostgreSQL:

```bash
psql -d iot_simulation
```

## Count records

```sql
SELECT COUNT(*) FROM telemetry_logs;
```

### Expected result

The number should increase while your listener is running.

---

## View latest rows

```sql
SELECT * 
FROM telemetry_logs
ORDER BY received_at DESC
LIMIT 10;
```

---

## View average values

```sql
SELECT 
    AVG(temperature) AS avg_temperature,
    AVG(humidity) AS avg_humidity,
    AVG(pressure) AS avg_pressure
FROM telemetry_logs;
```

---

## View min/max values

```sql
SELECT
    MIN(temperature) AS min_temperature,
    MAX(temperature) AS max_temperature,
    MIN(humidity) AS min_humidity,
    MAX(humidity) AS max_humidity,
    MIN(pressure) AS min_pressure,
    MAX(pressure) AS max_pressure
FROM telemetry_logs;
```

---

# 11. Export PostgreSQL Data to CSV

## Option A — Export from inside `psql`

```sql
\copy telemetry_logs TO 'analysis/exported_telemetry.csv' CSV HEADER;
```

### What it does

Exports the full `telemetry_logs` table to a CSV file with column headers.

---

## Option B — Export with selected columns

```sql
\copy (
    SELECT 
        id,
        temperature,
        humidity,
        pressure,
        topic,
        received_at
    FROM telemetry_logs
    ORDER BY received_at
) TO 'analysis/exported_telemetry.csv' CSV HEADER;
```

---

## Option C — Export from terminal directly

```bash
psql -d iot_simulation -c "\copy telemetry_logs TO 'analysis/exported_telemetry.csv' CSV HEADER"
```

---

# 12. Load CSV into Google Colab

In Google Colab:

```python
from google.colab import files

uploaded = files.upload()
```

Upload:

```text
exported_telemetry.csv
```

Then load it:

```python
import pandas as pd

df = pd.read_csv("exported_telemetry.csv")
df.head()
```

---

# 13. Starter Colab Analysis Script

Use this as the base for modifying your provided `iot_data_analysis.py`.

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv("exported_telemetry.csv")

# Preview data
print(df.head())
print(df.info())
print(df.describe())

# Convert timestamp column
df["received_at"] = pd.to_datetime(df["received_at"])

# Check missing values
print(df.isnull().sum())

# Basic statistics
summary = df[["temperature", "humidity", "pressure"]].agg([
    "count", "mean", "median", "min", "max", "std"
])

print(summary)

# Plot temperature over time
plt.figure(figsize=(12, 5))
plt.plot(df["received_at"], df["temperature"])
plt.title("Temperature Over Time")
plt.xlabel("Time")
plt.ylabel("Temperature")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot humidity over time
plt.figure(figsize=(12, 5))
plt.plot(df["received_at"], df["humidity"])
plt.title("Humidity Over Time")
plt.xlabel("Time")
plt.ylabel("Humidity")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot pressure over time
plt.figure(figsize=(12, 5))
plt.plot(df["received_at"], df["pressure"])
plt.title("Pressure Over Time")
plt.xlabel("Time")
plt.ylabel("Pressure")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Correlation analysis
correlation = df[["temperature", "humidity", "pressure"]].corr()
print(correlation)

# Histogram
df[["temperature", "humidity", "pressure"]].hist(figsize=(12, 8))
plt.tight_layout()
plt.show()

# Detect simple outliers using z-score
numeric_cols = ["temperature", "humidity", "pressure"]

for col in numeric_cols:
    mean = df[col].mean()
    std = df[col].std()
    df[f"{col}_zscore"] = (df[col] - mean) / std

outliers = df[
    (df["temperature_zscore"].abs() > 3) |
    (df["humidity_zscore"].abs() > 3) |
    (df["pressure_zscore"].abs() > 3)
]

print("Outliers:")
print(outliers)
```

---

# 14. Custom Analysis Ideas

Use these after the basic script works.

## 1. Rolling averages

```python
df["temperature_rolling_avg"] = df["temperature"].rolling(window=10).mean()

plt.figure(figsize=(12, 5))
plt.plot(df["received_at"], df["temperature"], label="Temperature")
plt.plot(df["received_at"], df["temperature_rolling_avg"], label="Rolling Avg")
plt.title("Temperature Rolling Average")
plt.xlabel("Time")
plt.ylabel("Temperature")
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

---

## 2. Sensor correlation heatmap with matplotlib

```python
corr = df[["temperature", "humidity", "pressure"]].corr()

plt.figure(figsize=(6, 5))
plt.imshow(corr)
plt.colorbar()
plt.xticks(range(len(corr.columns)), corr.columns, rotation=45)
plt.yticks(range(len(corr.columns)), corr.columns)
plt.title("Sensor Correlation Matrix")
plt.tight_layout()
plt.show()
```

---

## 3. Group by minute

```python
df["minute"] = df["received_at"].dt.floor("min")

minute_summary = df.groupby("minute")[["temperature", "humidity", "pressure"]].mean()

print(minute_summary.head())
```

---

## 4. Export cleaned analysis file

```python
df.to_csv("cleaned_telemetry_analysis.csv", index=False)
```

---

# 15. Kaggle Dataset Exploration

Search Kaggle for datasets using terms like:

```text
temperature humidity pressure dataset
weather sensor dataset
IoT temperature humidity dataset
environment sensor data
barometric pressure dataset
climate sensor dataset
```

## What to do with Kaggle data

1. Download a dataset.
2. Upload the CSV to Colab.
3. Load it with pandas.
4. Identify columns for temperature, humidity, and/or pressure.
5. Clean missing values.
6. Run summary statistics.
7. Plot trends and histograms.
8. Compare Kaggle data against your simulated data.

## Kaggle analysis starter

```python
import pandas as pd
import matplotlib.pyplot as plt

df_kaggle = pd.read_csv("your_kaggle_file.csv")

print(df_kaggle.head())
print(df_kaggle.info())
print(df_kaggle.describe())

# Adjust column names based on dataset
temperature_col = "temperature"

plt.figure(figsize=(10, 5))
plt.plot(df_kaggle[temperature_col])
plt.title("Kaggle Temperature Data")
plt.xlabel("Record Number")
plt.ylabel("Temperature")
plt.tight_layout()
plt.show()
```

---

# 16. PostgreSQL Common Commands Cheatsheet

## Connect to database

```bash
psql -d iot_simulation
```

## List databases

```sql
\l
```

## Connect to database inside psql

```sql
\c iot_simulation
```

## List tables

```sql
\dt
```

## Describe table

```sql
\d telemetry_logs
```

## Count rows

```sql
SELECT COUNT(*) FROM telemetry_logs;
```

## Show latest rows

```sql
SELECT * FROM telemetry_logs ORDER BY received_at DESC LIMIT 10;
```

## Delete all rows but keep table

```sql
TRUNCATE TABLE telemetry_logs;
```

## Drop table completely

```sql
DROP TABLE telemetry_logs;
```

## Drop database

```sql
DROP DATABASE iot_simulation;
```

## Exit psql

```sql
\q
```

---

# 17. Mosquitto Common Commands Cheatsheet

## Start Mosquitto

```bash
mosquitto -v
```

## Subscribe to a topic

```bash
mosquitto_sub -h localhost -t telemetry
```

## Publish a test message

```bash
mosquitto_pub -h localhost -t telemetry -m '{"temperature":72.5,"humidity":44.2,"pressure":1012.8}'
```

## Subscribe to all topics

```bash
mosquitto_sub -h localhost -t "#"
```

## Subscribe with verbose output

```bash
mosquitto_sub -h localhost -t telemetry -v
```

## Test broker port

```bash
nc -vz localhost 1883
```

Expected result:

```text
Connection to localhost port 1883 succeeded
```

---

# 18. Debugging Checklist

## Mosquitto Issues

### Problem: Publisher cannot connect

Check broker is running:

```bash
mosquitto -v
```

Check port:

```bash
nc -vz localhost 1883
```

---

### Problem: No messages appearing

Subscribe manually:

```bash
mosquitto_sub -h localhost -t telemetry -v
```

Then publish manually:

```bash
mosquitto_pub -h localhost -t telemetry -m '{"temperature":70,"humidity":50,"pressure":1010}'
```

---

## PostgreSQL Issues

### Problem: Database does not exist

```sql
CREATE DATABASE iot_simulation;
```

---

### Problem: Table does not exist

```sql
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id SERIAL PRIMARY KEY,
    temperature DOUBLE PRECISION NOT NULL,
    humidity DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION NOT NULL,
    topic TEXT DEFAULT 'telemetry',
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### Problem: Permission error

Try connecting with explicit user:

```bash
psql -U postgres -d iot_simulation
```

---

## Python Issues

### Problem: Module not found

Make sure virtual environment is active:

```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

---

### Problem: Subscriber runs but database is empty

Check:

1. Is Mosquitto running?
2. Is publisher running?
3. Is subscriber subscribed to `telemetry`?
4. Is database name correct?
5. Is table name correct?
6. Are insert statements committing?

---

# 19. Code Reading Requirement

For every provided script, read it line by line.

## For each file, answer these questions

| Question | Notes |
|---|---|
| What imports are used? | Example: `paho.mqtt`, `psycopg2`, `json`, `time` |
| What configuration values exist? | Broker host, port, topic, database name |
| What functions exist? | Example: `on_connect`, `on_message`, `insert_data` |
| What does each function do? | Explain in your own words |
| Where is data generated? | Usually in publisher |
| Where is MQTT used? | Publish/subscribe |
| Where is SQL used? | Insert/query database |
| Where can it fail? | Connection, JSON parsing, database insert |
| What should be logged? | Messages received, inserts completed, errors |

---

## If You Do Not Understand a Code Segment

Send this to the group:

```text
Hi everyone,

I am reviewing the IoT MQTT/PostgreSQL code and I am trying to understand the following segment:

[PASTE CODE SEGMENT HERE]

My current understanding is:
[WRITE WHAT YOU THINK IT DOES]

Can someone help confirm whether I am understanding this correctly or explain what I am missing?

Thanks.
```

---

# 20. End-to-End Verification Checklist

Use this before saying the setup is complete.

## Environment

- [ ] Project folder exists
- [ ] Python virtual environment created
- [ ] Virtual environment activated
- [ ] Required Python packages installed
- [ ] `requirements.txt` created

## Mosquitto

- [ ] Mosquitto installed
- [ ] Mosquitto broker running
- [ ] Port `1883` open
- [ ] Manual `mosquitto_pub` test works
- [ ] Manual `mosquitto_sub` receives messages

## PostgreSQL

- [ ] PostgreSQL installed
- [ ] PostgreSQL service running
- [ ] `iot_simulation` database created
- [ ] Connected to `iot_simulation`
- [ ] `telemetry_logs` table created
- [ ] Table schema verified with `\d telemetry_logs`

## Publisher

- [ ] `publisher.py` runs without error
- [ ] Publisher connects to Mosquitto
- [ ] Publisher sends messages to topic `telemetry`
- [ ] Messages contain temperature, humidity, and pressure

## Subscriber

- [ ] `subscriber.py` runs without error
- [ ] Subscriber connects to Mosquitto
- [ ] Subscriber subscribes to `telemetry`
- [ ] Subscriber receives messages
- [ ] Subscriber parses JSON correctly
- [ ] Subscriber inserts rows into PostgreSQL

## Database Verification

- [ ] `SELECT COUNT(*) FROM telemetry_logs;` returns more than 0
- [ ] Latest records appear with `ORDER BY received_at DESC`
- [ ] Temperature values look reasonable
- [ ] Humidity values look reasonable
- [ ] Pressure values look reasonable

## CSV Export

- [ ] CSV exported successfully
- [ ] CSV has headers
- [ ] CSV includes `temperature`, `humidity`, `pressure`, and `received_at`
- [ ] CSV opens correctly
- [ ] CSV uploaded to Google Colab

## Colab Analysis

- [ ] CSV loaded with pandas
- [ ] `df.head()` works
- [ ] `df.info()` works
- [ ] `df.describe()` works
- [ ] Missing values checked
- [ ] At least one plot created
- [ ] Correlation analysis completed
- [ ] Outlier check completed
- [ ] Notes written explaining what the data shows

## Kaggle Extension

- [ ] Found relevant Kaggle dataset
- [ ] Downloaded Kaggle CSV
- [ ] Loaded Kaggle CSV in Colab
- [ ] Identified useful columns
- [ ] Ran basic statistics
- [ ] Created at least one visualization
- [ ] Compared Kaggle dataset with simulated IoT data

---

# 21. Recommended Learning Order

1. Understand what MQTT does.
2. Run Mosquitto manually.
3. Test `mosquitto_pub` and `mosquitto_sub`.
4. Understand the publisher code.
5. Understand the subscriber code.
6. Create PostgreSQL database/table manually.
7. Verify inserts manually with SQL.
8. Export data to CSV.
9. Analyze CSV in Google Colab.
10. Explore Kaggle datasets.
11. Build your own SQL and Mosquitto cheatsheet from repeated practice.

---

# 22. One-Line Full Workflow Reminder

```text
Start Mosquitto → Start PostgreSQL → Activate Python venv → Run subscriber → Run publisher → Verify PostgreSQL rows → Export CSV → Upload to Colab → Analyze
```
