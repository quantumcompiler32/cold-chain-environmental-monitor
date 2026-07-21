# Publisher and Subscriber

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Publisher simulator

File:

```text
src/arduino_events_simulate.py
```

Run:

```bash
iot simulator
```

The simulator publishes two device types every five seconds:

- `arduino-dht22` — temperature and humidity.
- `esp32-bmp280` — temperature and pressure.

Example payload:

```json
{
  "device_id": "arduino-dht22",
  "timestamp": "2026-06-22T14:15:00",
  "temperature": 74.32,
  "humidity": 48.21,
  "status": "online"
}
```

## Subscriber service

File:

```text
src/subscriber_arduinoevents.py
```

Run:

```bash
iot subscriber
```

The subscriber:

1. Connects to MQTT with retry logic.
2. Subscribes to `devices/+/telemetry`.
3. Parses JSON.
4. Validates `device_id`.
5. Inserts values into PostgreSQL with parameterized SQL.
6. Continues listening after a malformed message or temporary insertion failure.

## Easiest way to run both

```bash
iot go
```

This opens separate Terminal windows for:

- Subscriber
- Simulator
- Live PostgreSQL data

Stop each foreground process with `Ctrl+C`.

---

Next: [[Daily Startup and Shutdown]] · [[Verification Checklist]]
