# Simple Command System

[[00 - IoT Simulation Environment Setup|← IoT Home]]

## Two shortcut names

Both are identical:

```bash
iot help
io help
```

## Plain-word commands

| Plain word | Action |
|---|---|
| `iot setup` | Install and initialize everything |
| `iot on` | Start MQTT and PostgreSQL |
| `iot off` | Stop project processes and services |
| `iot go` | Start and open the full pipeline |
| `iot see` | Show recent telemetry |
| `iot watch` | Refresh telemetry continuously |
| `iot save` | Export CSV |
| `iot upload` | Export, reveal CSV, and open Colab |
| `iot doctor` | Diagnose the environment |
| `iot fix` | Repair packages, services, and schema |
| `iot menu` | Open a numbered interactive menu |

## Supported synonyms

```text
on       = start
'off'    = stop
'go'     = run, launch, demo
'see'    = data, get, view
'save'   = export, download, backup
'postgres' = db, database, postgresql
'doctor' = check, health
'fix'    = repair
```

Examples:

```bash
io go
iot view
iot download
iot database
iot repair
```

## Virtual environment behavior

Normal commands automatically execute:

```text
venv/bin/python
```

To activate manually in the current shell:

```bash
iot activate
```

To leave the environment:

```bash
iot deactivate
```

## Interactive menu

```bash
iot menu
```

Use the menu when you do not remember a command.

---

Full list: [[Command Cheat Sheet]]
