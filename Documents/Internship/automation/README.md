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

## Local refresh

`projects.toml` lists each project’s source roots and rule file. Run a local-only refresh for the active project:

```bash
python3 automation/vault_refresh.py
```

To refresh a registered project by ID:

```bash
python3 automation/vault_refresh.py --project bytesmart
```

Refresh writes one current source registry and a meaningful activity log inside the vault. It does not copy, modify, or delete original source files, and it skips unchanged sources using local timestamps, file sizes, and hashes.

Run the normal local maintenance sequence—Refresh, Review, then dashboard health—with one command:

```bash
python3 automation/vault_maintenance.py
```

Install the daily 8:00 AM macOS job with:

```bash
zsh automation/install_vault_refresh_agent.sh
```

The daily job runs only local refresh, Review, and dashboard health. Its logs are `automation/vault-refresh.log` and `automation/vault-refresh-error.log`.

To add a future project, add one `[[project]]` entry to `projects.toml` with its ID, title, source roots, rule file, dashboard note, work-queue note, and active state. The refresh code and note model stay shared. The central Source Registry preserves each project's rows when another project refreshes.

`external_sources.toml` holds metadata-only Gmail and Google Drive references for each project. Refresh adds those rows to the same source registry without downloading, copying, or summarizing their content.

## Review queue

Build the readable local Review queue after a refresh:

```bash
python3 automation/vault_review.py
```

It collects only source rows that need a human classification and decision notes whose status is `Pending` or `Defer`. It creates one queue, not a note for every unresolved item, and makes no model calls.

To keep a source decision, add the exact source path from the registry as a `reference` entry in `bytesmart_vault_overrides.toml`. Valid note metadata still wins over an override; overrides win over ordinary matching rules.

## Rebuild preview

Preview proposed moves of existing vault copies without changing anything:

```bash
python3 automation/vault_rebuild.py --write-preview
```

Only `--apply --confirm` moves the proposed vault copies. Use `--only 'folder/file.ext'` to narrow the plan. Linked copies are held for manual migration so existing vault navigation stays intact; live project sources and protected note content are never candidates.
