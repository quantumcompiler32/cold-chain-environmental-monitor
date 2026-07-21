# MQTT Problems

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Connection refused on port 1883

```bash
iot on
iot mqtt
iot logs
```

## Test publishing

```bash
iot mqtt-test
```

If the subscriber is running, confirm the test event reaches PostgreSQL:

```bash
iot see
```

## Port already in use

```bash
lsof -nP -iTCP:1883 -sTCP:LISTEN
```

The command system uses an existing broker when one is already listening. If that broker is misconfigured, stop it and restart:

```bash
brew services stop mosquitto 2>/dev/null || true
iot restart
```

## Mosquitto executable missing

```bash
brew install mosquitto
iot fix
```

## Watch logs

```bash
iot logs
```

---

Related: [[Mosquitto Setup]] · [[Port and Service Problems]]
