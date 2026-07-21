# Python Environment

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Automatic setup

```bash
iot setup
```

## Manual setup

```bash
cd "/full/path/to/this/project"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Correct activation path:

```bash
source venv/bin/activate
```

Common incorrect commands:

```bash
source/bin/activate
source ~/install_iot_shortcuts.sh
```

## Required packages

- `paho-mqtt` — MQTT client.
- `psycopg2-binary` — PostgreSQL client.
- `python-dotenv` — loads `.env` settings.
- `requests` — general HTTP support for future extensions.
- `pandas`, `numpy`, `matplotlib` — analytics.

## Verify packages

```bash
iot python-check
```

Manual verification:

```bash
source venv/bin/activate
python -c "import paho.mqtt.client, psycopg2, pandas, numpy, matplotlib; print('All imports work')"
```

## Why `ModuleNotFoundError: No module named 'paho'` happens

The script was executed with a Python interpreter that does not contain `paho-mqtt`.

Preferred fix:

```bash
iot fix
```

Manual fix:

```bash
cd "/full/path/to/this/project"
source venv/bin/activate
python -m pip install -r requirements.txt
python src/subscriber_arduinoevents.py
```

> [!tip]
> Run `iot subscriber` instead of manually calling Python. The shortcut always uses this project's virtual environment.

---

Related: [[Publisher and Subscriber]] · [[Python and Virtual Environment Problems]]
