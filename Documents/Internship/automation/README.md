# Internship Organizer

This standard-library Python tool copies eligible files from:

`/Users/mokshjoshi/Documents/EverythingLife/Internship`

into the Obsidian vault’s `Artifacts/` categories without deleting or modifying the originals.

## Manual run

```bash
python3 automation/internship_organizer.py
```

## Watch mode

```bash
python3 automation/internship_organizer.py --watch
```

The macOS login service uses watch mode. Ambiguous files go to `Artifacts/Inbox/`; the generated `Imported Internship Files.md` manifest is the review queue.

Ignored for safety and search quality: `.env`, `.DS_Store`, `.venv`, caches, compiled files, dependency metadata, and build directories.

## ByteSmart vault rules

`bytesmart_vault_rules.toml` is the readable local rule set for the new ByteSmart vault structure. It defines the seven visible branches and supports deterministic filename, path, extension, and heading matches. Explicit frontmatter and manual overrides always win over a rule.

Validate the rules without scanning files or changing the vault:

```bash
python3 automation/vault_rules.py --check-rules automation/bytesmart_vault_rules.toml
```

This command uses only the Python standard library and makes no model calls.
