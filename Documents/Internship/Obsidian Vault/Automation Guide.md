---
tags: [internship, automation, reference]
---

# Automation Guide

## Current behavior

The current organizer watches `/Users/mokshjoshi/Documents/EverythingLife/Internship` after login. It copies eligible new files into the vault, classifies them with the existing artifact categories, preserves original filenames, and regenerates the imported-file manifest.

## Categories

- **ByteSmart** — ByteSmart project notes and workflows
- **IoT Simulation** — MQTT, Mosquitto, PostgreSQL, scripts, operations, and troubleshooting
- **Reports** — meeting notes, professionalism, daily reports, and outreach material
- **Data and Research** — CSV, JSON, notebooks, model files, and telemetry
- **Code and Automation** — general scripts and configuration not specific to another project
- **Notes and Learning** — learning notes and cheatsheets
- **Reference Material** — PDFs, documents, presentations, HTML, and plain references
- **Inbox** — ambiguous files requiring review

## Manual commands

```bash
python3 /Users/mokshjoshi/Documents/Internship/automation/internship_organizer.py
python3 /Users/mokshjoshi/Documents/Internship/automation/internship_organizer.py --watch
```

The organizer never deletes or edits source files. It ignores `.env`, `.DS_Store`, virtual environments, caches, compiled files, build directories, and dependency metadata.

## Review loop

Open [[Imported Internship Files]] after creating or receiving new work. Anything under [[Imported Internship Files#Inbox|Inbox]] is intentionally waiting for a human category decision.

## ByteSmart vault rules

The new seven-branch ByteSmart rules are stored in `automation/bytesmart_vault_rules.toml`. They can be validated locally without AI, but they are not connected to the automatic refresh yet.

The next automation slice will use those rules to update the ByteSmart branch pages, source registry, activity log, and Review queue while leaving the live source directory unchanged.
