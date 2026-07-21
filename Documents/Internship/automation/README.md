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
