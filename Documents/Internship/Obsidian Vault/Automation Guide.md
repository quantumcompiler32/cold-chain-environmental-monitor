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

The seven-branch ByteSmart rules are stored in `automation/bytesmart_vault_rules.toml`. They can be validated locally without AI.

The local refresh command now uses these rules to update the central source registry and meaningful activity log while leaving the live source directory unchanged:

```bash
python3 /Users/mokshjoshi/Documents/Internship/automation/vault_refresh.py
```

The existing login watcher still maintains the older `Artifacts` copies. It will be replaced only after the ByteSmart refresh workflow is fully verified.

Gmail and Google Drive references live in `automation/external_sources.toml`. Refresh adds their metadata to the same registry without depending on connector access or copying external content.

## Review queue

After a refresh, build the one readable review page with:

```bash
python3 /Users/mokshjoshi/Documents/Internship/automation/vault_review.py
```

[[Review Queue]] contains only unclear source classifications and decisions marked `Pending` or `Defer`. It does not create a separate note for every item and does not use AI.

## Daily and on-demand maintenance

Use this normal on-demand command whenever you want the vault updated:

```bash
python3 /Users/mokshjoshi/Documents/Internship/automation/vault_maintenance.py
```

The optional macOS job runs the same local Refresh and Review sequence every day at 8:00 AM. Install it once with:

```bash
zsh /Users/mokshjoshi/Documents/Internship/automation/install_vault_refresh_agent.sh
```

It makes no model calls, does not fetch external content, and writes only the source registry, Review queue, and meaningful activity when relevant.
