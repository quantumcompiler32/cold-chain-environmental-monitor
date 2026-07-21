# Port and Service Problems

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Check both ports

```bash
iot status
```

Manual checks:

```bash
lsof -nP -iTCP:1883 -sTCP:LISTEN
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

## Restart the project

```bash
iot restart
```

## Show Homebrew services

```bash
brew services list | grep -E 'mosquitto|postgresql'
```

## Stop a conflicting Homebrew Mosquitto service

The project can run its own broker, so a broken global service is not required:

```bash
brew services stop mosquitto 2>/dev/null || true
iot restart
```

## Kill only project Python processes

```bash
iot kill
```

This targets the subscriber and simulator files inside the current project path.

---

Related: [[MQTT Problems]] · [[PostgreSQL Problems]]
