# Daily Startup and Shutdown

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Fast startup

```bash
iot go
```

This starts infrastructure and opens the project windows.

## Manual multi-terminal workflow

### Terminal 1 — subscriber

```bash
iot subscriber
```

### Terminal 2 — simulator

```bash
iot simulator
```

### Terminal 3 — live data

```bash
iot watch
```

### Optional Terminal 4 — MQTT logs

```bash
iot logs
```

## Stop foreground applications

Press:

```text
Ctrl+C
```

inside subscriber, simulator, watcher, and log windows.

## Stop project services

```bash
iot off
```

`iot off` stops project Python processes, the project-started Mosquitto broker, and the Homebrew PostgreSQL service.

## Restart

```bash
iot restart
```

## Confirm status

```bash
iot status
```

Expected:

- MQTT port `1883` is open.
- PostgreSQL port `5432` is open.
- Database query succeeds.

---

Related: [[Verification Checklist]] · [[Command Cheat Sheet]]
