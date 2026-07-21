# Troubleshooting Index

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Start with automatic diagnosis

```bash
iot doctor
```

Then attempt safe repair:

```bash
iot fix
```

## Choose the problem

- Command not found, `io help`, or incorrect `source`: [[Shortcut and Installation Problems]]
- `ModuleNotFoundError`, pip, or activation: [[Python and Virtual Environment Problems]]
- Broker connection, port 1883, or publish failures: [[MQTT Problems]]
- Database connection, role, table, or port 5432: [[PostgreSQL Problems]]
- Address already in use or service conflicts: [[Port and Service Problems]]

## Universal reset sequence

This does not delete telemetry data:

```bash
cd "/full/path/to/IoT_Simulation_Obsidian_Final_Updated"
bash scripts/install_iot_shortcuts.sh
source ~/.zshrc
iot fix
iot doctor
```

---

Reference: [[Command Cheat Sheet]]
