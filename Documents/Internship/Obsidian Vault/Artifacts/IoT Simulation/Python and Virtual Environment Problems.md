# Python and Virtual Environment Problems

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Error: `ModuleNotFoundError: No module named 'paho'`

Preferred repair:

```bash
iot fix
```

Manual repair:

```bash
cd "/full/path/to/project"
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import paho.mqtt.client as mqtt; print('paho works')"
```

Then run:

```bash
iot subscriber
```

## Wrong activation command

Correct:

```bash
source venv/bin/activate
```

Incorrect:

```bash
source/bin/activate
```

## Confirm which Python is active

```bash
which python
python --version
python -m pip --version
```

When manually activated, the paths should point inside this project’s `venv/` directory.

## PEP 668 externally managed environment

Do not install packages into macOS system Python. Use the project virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

## Rebuild the environment

```bash
iot rebuild-venv
```

This deletes only `venv/` and reinstalls Python packages. It does not delete the database or exported data.

---

Related: [[Python Environment]]
