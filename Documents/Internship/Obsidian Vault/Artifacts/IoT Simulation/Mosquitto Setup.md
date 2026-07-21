# Mosquitto Setup

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## What the project does

The command system starts a project-local Mosquitto process using:

```text
config/mosquitto-local.conf
```

This avoids depending on edits to the global Homebrew configuration file. If another broker is already listening on port `1883`, the project uses that broker instead of starting a duplicate.

## Simple commands

```bash
iot on           # Start MQTT and PostgreSQL
iot mqtt         # Show MQTT status
iot mqtt-test    # Publish one test payload
iot logs         # Follow MQTT logs
iot off          # Stop project processes and services
```

## MQTT topic model

```text
devices/<device-id>/telemetry
```

Examples:

```text
devices/arduino-dht22/telemetry
devices/esp32-bmp280/telemetry
```

Subscriber wildcard:

```text
devices/+/telemetry
```

## Manual broker test

Terminal 1:

```bash
mosquitto_sub -h localhost -p 1883 -t 'devices/+/telemetry' -v
```

Terminal 2:

```bash
mosquitto_pub -h localhost -p 1883 \
  -t 'devices/test-device/telemetry' \
  -m '{"device_id":"test-device","temperature":72.5,"humidity":45.2,"status":"online"}'
```

## Local configuration

```conf
listener 1883 127.0.0.1
allow_anonymous true
persistence false
connection_messages true
log_type all
```

This local-only listener is appropriate for the assignment. Do not expose anonymous MQTT to an untrusted network.

## Logs

```bash
iot logs
```

Project log file:

```text
logs/mosquitto.log
```

---

Troubleshooting: [[MQTT Problems]] · [[Port and Service Problems]]
