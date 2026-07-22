---
type: decision
project: ByteSmart
branch: Findings & Decisions
status: Active
source:
  - [[Vault Design Decisions]]
  - [[Internship Context And Glossary]]
created: 2026-07-21
updated: 2026-07-21
confidence: high
review: false
---

# ByteSmart Vault Specification

## What this is

This is the build specification for the ByteSmart Obsidian vault. The vault should make it easy to find useful information, understand what is happening now, see what comes next, and keep connected material organized without becoming cluttered or dependent on AI.

## Why it matters

ByteSmart work currently exists across local files, reports, email, Drive, code, data, and notes. The vault becomes the clear place to understand the project while the live project directory remains the source of truth for original files.

## Success criteria

- A person can open the dashboard and quickly see current work, pending decisions, meaningful recent changes, and system health.
- Every important source is traceable through one central source registry.
- Useful information is promoted into concise canonical notes; duplicate summaries and unnecessary notes are avoided.
- The vault works with AI disabled.
- Daily refreshes consume no model tokens unless AI is explicitly enabled.
- A rebuild previews changes before applying them and never alters original source files.
- ByteSmart is the current visible project identity. Bitwise material is organized inside ByteSmart.
- Future projects can be added without duplicating the vault architecture or mixing their sources into ByteSmart.

## Information architecture

The vault uses these seven visible branches:

1. **Current Work** — active work, next actions, blockers, waiting items, completed work, and scale ideas.
2. **Connected Sources** — source registry, Gmail and Drive references, local paths, authority, coverage, sensitivity, and sync state.
3. **System & Sensors** — architecture, hardware, services, inputs, outputs, thresholds, failure modes, and operating notes.
4. **Data Pipeline & Storage** — collection, schemas, validation, transformations, MQTT, databases, storage, and backups.
5. **Analysis & Models** — questions, datasets, EDA, visualizations, statistics, models, evaluation, and limitations.
6. **Findings & Decisions** — evidence-backed findings, design decisions, tradeoffs, risks, contradictions, and caveats.
7. **Deliverables & Visuals** — reports, slides, diagrams, demos, dashboards, and their review status.

Each branch has one landing page. Subfolders remain shallow and exist only when they make browsing easier. Branch pages are curated navigation hubs, not raw inventories.

## Visual navigation

The command center and branch hubs use a restrained color system so they are easier to scan without changing the content or adding visual clutter. Each branch keeps one stable accent: blue for Current Work, teal for Connected Sources, orange for System & Sensors, violet for Data Pipeline & Storage, green for Analysis & Models, amber for Findings & Decisions, and magenta for Deliverables & Visuals. Color supports headings, links, and navigation only; meaning must remain clear in plain text and work in any Obsidian theme.

## Navigation and graph rules

- The main entry page is titled **ByteSmart Command Center**.
- The dashboard shows Current Work, Decisions, Sync Health, meaningful activity, branch navigation, and full search.
- The normal dashboard actions are `Refresh`, `Review`, and `Rebuild`.
- A canonical note links to its branch hub, only the evidence needed to support it, and at most three genuinely useful related notes.
- The graph is intentionally minimal. Links are created only when they improve understanding, action, or provenance.
- The source registry is one readable note with an automation-managed table, not one note per source.

## Canonical notes

A canonical note is created only when it adds durable value for retrieval, execution, analysis, a decision, or provenance. Automation must update an existing suitable note before creating another.

Every canonical note has this metadata:

```yaml
type:
project: ByteSmart
branch:
status:
source:
created:
updated:
confidence:
review:
```

The allowed note types are:

`project`, `index`, `source`, `topic`, `work-item`, `finding`, `decision`, `deliverable`, and `review`.

Every canonical note starts with a short plain-language explanation of what it is, what changed or was learned, and why it matters. The rest of the structure depends on its type:

| Type | Required useful content |
|---|---|
| Work item | outcome, status, next action, blockers |
| Finding | finding, evidence, analysis, limitations, implications |
| Decision | question, options, rationale, result |
| Deliverable | audience, purpose, current version, review status |
| Source | provenance, authority, coverage, sensitivity, sync status |

## Writing rules

- Write in clear, natural language that is easy for Moksh to understand.
- Use formal language when a source or deliverable requires it, but explain the meaning plainly.
- Preserve exact code, filenames, commands, measurements, and quoted evidence.
- Separate source facts from inference and uncertainty.
- Do not use emojis, corporate filler, artificial decoration, or unsupported claims.
- Never rewrite Moksh’s existing writing unless asked.

Protected human-authored headings are `Interpretation`, `Decision`, `Next Steps`, `Caveats`, and `Human Notes`. Existing unmarked content is protected by default. Automation may update only explicit managed sections and metadata.

## Sources and reconstruction

Every connected artifact receives a source-record row with:

| Field | Purpose |
|---|---|
| Source ID | stable identifier |
| Title | readable name |
| Type | local file, Gmail, Drive, dataset, code, or reference |
| Reference | local path or external reference |
| Branch | most useful ByteSmart branch |
| Authority | `Primary`, `Supporting`, or `Unverified` |
| Coverage | `Complete`, `Partial`, or `Unknown` |
| Sensitivity | `Normal`, `Sensitive`, or `Restricted` |
| Last checked | last successful check |
| Content hash | detects meaningful changes |
| Sync status | current, changed, unavailable, or needs review |
| Promotion status | registry only, promoted, or review |

Status reports are useful first-party evidence but are not assumed to be complete. Reconstruction cross-checks reports against code, local files, Gmail, Drive, datasets, notebooks, deliverables, and existing notes. Work missing from a report may be added when supported by evidence; the report remains unchanged and its coverage is marked `Partial`.

Connected-source notes are current-version-only. When a source changes, the system updates the current canonical note and keeps only the current reference, latest hash, detection time, and refreshed-note record. It does not retain prior summaries or source text unless explicitly archived.

`Restricted` sources keep metadata and references only until Moksh explicitly approves content processing.

## Local-first automation

The vault must remain fully useful without AI.

Local deterministic automation owns:

- file discovery and change detection;
- hashes, timestamps, frontmatter, and source registry updates;
- rule-based location and note-type classification;
- branch and dashboard indexes;
- explicit status updates;
- broken-link, stale-status, and uncategorized-item audits;
- meaningful activity logging; and
- review and decision queues.

Local classification priority is:

1. explicit note metadata or manual placement;
2. explicit override;
3. readable categorization rules based on path, file extension, filename, headings, and known ByteSmart terms;
4. Inbox with a reason when uncertain or conflicting.

Local rules may not invent findings, summaries, or decisions.

Categorization rules live in one readable, validated, versioned configuration file under `automation/`. Explicit metadata and overrides always win.

## Scaling to other projects

The vault starts with ByteSmart, but the automation is project-aware. A local project registry will define each project’s stable ID, display title, source roots, rule file, and active state.

- Each project uses the same seven branches, note templates, source fields, review flow, and local refresh behavior.
- Every note keeps a `project` field, so shared branch pages can filter and link to project-specific work without duplicating knowledge.
- Local change detection is scoped to each project’s source roots. Adding a project does not cause a full rescan of unrelated projects or consume AI tokens.
- ByteSmart stays the normal dashboard while it is the only active project. A portfolio or projects index is created only when a second project needs it.
- A project may have its own rules file, but the validator and organizer code remain shared.

## Optional AI

AI is opt-in. It may be used for high-value summaries, semantic classification, ambiguity resolution, suggested links, and clear-first rewriting. When AI is disabled or unavailable, those items remain in Review and no other part of the vault stops working.

The daily refresh starts locally and uses no AI by default. If enabled, the daily budget is:

- 10 model calls maximum;
- 25,000 input tokens maximum; and
- 5,000 output tokens maximum.

The system stops at the first limit and queues lower-priority work. Larger on-demand jobs show estimates for files, calls, input tokens, and output tokens before approval. Full rebuilds always require explicit approval.

## Refresh, review, and rebuild

### Refresh

Refresh processes changed local material, updates managed metadata and indexes, and records only meaningful activity. It does not create a daily note merely because a refresh occurred.

### Review

Review collects ambiguous classifications, source conflicts, missing provenance, AI suggestions, and decisions. A decision uses `pending`, `approved`, `rejected`, or `defer`. `defer` means leave the decision open without applying its proposed change.

### Rebuild

Rebuild is an on-demand reorganization pass. Before any change, it previews:

- files that would move or receive metadata;
- notes that would change;
- unresolved or ambiguous items;
- protected content left untouched; and
- estimated AI usage, when enabled.

Moksh can apply, narrow, or cancel the rebuild. Rebuild never changes original live-source files.

## Activity and dashboard health

The vault has one central activity log. It records only meaningful changes: work progress, blockers, decisions, deliverables, source changes, findings, and automation errors. Entries remain as compact searchable records and may be filtered or collapsed when old.

The dashboard displays:

- active, next, waiting, and blocked work;
- pending decisions;
- last refresh and system health;
- changed, skipped, and review items;
- token usage only when AI was used; and
- meaningful recent activity.

## Migration from the current vault

The source directory `/Users/mokshjoshi/Documents/EverythingLife/Internship` remains untouched.

The current generic `Artifacts` copies are reclassified into the seven branches only where that improves discovery. Unclear material remains in one visible archive or unclassified area. Existing category indexes become redirects or are removed only after branch navigation and links have been verified. Migration must not create extra copies just to satisfy the new layout.

## External sources

Gmail and Google Drive are connected sources, but local background automation must not depend on Codex connector access. The local organizer handles local files independently. External source sync is a user-approved connector or import operation until an authenticated local integration is deliberately configured.

## Non-goals

- Replacing original project files with vault copies.
- Automatically rewriting protected notes.
- Creating a note for every email, file, or refresh.
- Making medical, safety, potency, or product-release decisions from ByteSmart sensor or model output.
- Depending on AI or a specific Obsidian plugin for the vault to work.

## Definition of done

The implementation is complete when the seven branches, dashboard, source registry, activity log, review queue, templates, deterministic rules, preview-first rebuild, and local refresh work together; the existing ByteSmart material is migrated safely; tests cover classification, preservation, indexing, override behavior, and no-AI operation; and the results are visually checked in Obsidian.

## Related notes

- [[Vault Design Decisions]]
- [[Internship Context And Glossary]]
- [[Automation Guide]]
