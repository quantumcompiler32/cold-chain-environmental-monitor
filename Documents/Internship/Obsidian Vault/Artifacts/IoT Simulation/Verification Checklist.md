# Verification Checklist

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## One-command health check

```bash
iot doctor
```

## Infrastructure checklist

- [ ] Homebrew is installed.
- [ ] Mosquitto executable is available.
- [ ] PostgreSQL executable is available.
- [ ] Port `1883` is listening.
- [ ] Port `5432` is listening.

## Python checklist

- [ ] `venv/bin/python` exists.
- [ ] `paho.mqtt.client` imports successfully.
- [ ] `psycopg2` imports successfully.
- [ ] `pandas`, `numpy`, and `matplotlib` import successfully.

## Data-flow checklist

1. Start services:

   ```bash
   iot on
   ```

2. Start subscriber:

   ```bash
   iot subscriber
   ```

3. In another Terminal, publish one test event:

   ```bash
   iot mqtt-test
   ```

4. Confirm the row:

   ```bash
   iot see
   ```

5. Run the simulator and watch rows increase:

   ```bash
   iot simulator
   iot count
   ```

## Analytics checklist

```bash
iot save
iot analyze
iot upload
```

- [ ] A timestamped CSV appears under `exports/`.
- [ ] Charts appear under `exports/charts/`.
- [ ] Colab opens and the CSV can be uploaded.

---

Fix failures: [[Troubleshooting Index]]
