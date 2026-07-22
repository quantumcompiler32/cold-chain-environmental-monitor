# Connected Project Vault

This project organizes multiple connected projects in one Obsidian vault while keeping live project files as the authoritative source. The vault adds context, navigation, provenance, decisions, and project-management views.

## Language

### Vault concepts

**Project**:
A bounded body of work identified on every canonical note. ByteSmart is the current project; Bitwise-related material belongs inside ByteSmart rather than forming a separate project or navigation layer. Future projects use the same vault model without mixing their notes into ByteSmart.

**Project registry**:
The local configuration that identifies each project, its title, source roots, rules file, and active state. It lets one vault and one refresh system support multiple projects without reprocessing unrelated material.

**Branch**:
One of the seven shared navigation areas: Current Work, Connected Sources, System & Sensors, Data Pipeline & Storage, Analysis & Models, Findings & Decisions, or Deliverables & Visuals.

**Canonical note**:
A durable, current-first curated explanation of a concept, work item, source, finding, decision, or deliverable. It is not a copy of every source artifact or a history of every prior summary.

**Source record**:
A provenance entry that identifies an original local, Gmail, Google Drive, dataset, or reference source and records its authority, verification, sensitivity, and synchronization state.

**Coverage**:
An assessment of how much of the relevant work a source captures: `Complete`, `Partial`, or `Unknown`. Authority describes where information came from; coverage describes whether the source is a complete account.

**Promotion threshold**:
The rule that a source becomes a standalone canonical note only when it adds durable value for future retrieval, execution, analysis, a decision, or provenance. Otherwise it remains a lightweight registry entry or activity record.

**Curated graph**:
A deliberately limited set of useful links between project indexes, branch indexes, canonical notes, work items, evidence, findings, decisions, and deliverables. It avoids automatic links between every related-looking item.

**Source registry**:
One readable Markdown note containing the source records for the project. A source receives its own canonical note only when it passes the promotion threshold.

**Meaningful activity**:
A change worth seeing later because it affects work, a blocker, a decision, a deliverable, a source, a finding, or automation reliability. Routine refreshes do not qualify on their own.

**Activity retention**:
Meaningful activity stays in the central log as compact entries. It may be filtered or collapsed, but it is not removed merely because it is old.

**Daily automation budget**:
The automatic daily refresh makes no model calls when nothing changed, then stops at 10 model calls, 25,000 input tokens, or 5,000 output tokens, whichever comes first. Remaining work waits for review or an on-demand run.

**AI-optional automation**:
The vault's core synchronization, organization, indexing, auditing, and decision-queue behavior works locally without AI. AI accelerates summaries, semantic classification, ambiguity resolution, and clear-first rewriting, but its absence never blocks the system.

**AI opt-in**:
The daily refresh runs locally by default. AI is enabled only for a specific task or an explicitly approved on-demand run.

**Deterministic categorization**:
Local-only categorization uses explicit frontmatter or placement first, then file paths, extensions, filenames, headings, and known ByteSmart terms. It can classify location and note type, but it does not invent findings, summaries, or decisions.

**Categorization rules**:
Human-readable, validated mappings that control deterministic categorization independently of the automation code. Explicit note metadata takes priority over these rules.

**Explicit override**:
A manual correction to an automation-managed value. It remains in effect across synchronization until the user removes or changes the override.

**Simple-by-default use**:
The vault exposes a small set of plain-language actions and views while keeping hashes, token budgets, prompts, and synchronization details available only when they help diagnose or control the system.

**Primary actions**:
The normal dashboard exposes `Refresh`, `Review`, and `Rebuild`. Other controls are secondary and do not clutter the normal workflow.

**Rebuild preview**:
Before applying a larger organization pass, the system shows proposed file and note changes, ambiguous items, protected content it will leave alone, and estimated model usage when AI is enabled.

**Shallow navigation**:
Each branch has one landing page and only shallow subfolders that improve browsing. Detail is handled through meaningful links, metadata, and search rather than deep nesting.

**Preserve-first migration**:
Existing source files remain untouched while vault copies and notes are reorganized. Useful material is promoted into the seven branches; unclear material remains accessible in one archive or unclassified area until the new structure is verified.

**Managed section**:
A clearly marked part of a note that automation may update. Handwritten interpretation, decisions, notes, and next steps remain protected.

**Protected sections**:
The human-authored sections `Interpretation`, `Decision`, `Next Steps`, `Caveats`, and `Human Notes`. Automation does not rewrite these sections; existing unmarked note content is protected by default.

**Review queue**:
The holding area for ambiguous classifications, contradictions, low-confidence changes, and decisions that require Moksh's approval.

**Decision queue**:
The dashboard view of unresolved choices. A decision is resolved with an explicit field such as `approved`, `rejected`, or `defer`; `defer` leaves it open without applying the proposed change.

**Daily refresh**:
An incremental synchronization that starts with local file events, timestamps, hashes, and diffs, then uses model calls only for changed or ambiguous material.

**On-demand sync**:
A user-triggered synchronization scoped to selected files, projects, branches, or a requested rebuild.

**New-note intake**:
The content-preserving process for notes without metadata: add metadata and file the note when classification is high-confidence, otherwise place it in Inbox with a suggested classification.

**High-confidence automation**:
An automated change supported by clear evidence and a stable classification rule. It may be applied without approval; uncertain changes go to Review.

**Sensitivity level**:
A source-handling classification: `Normal`, `Sensitive`, or `Restricted`.

**Normal**:
Source content may be summarized and linked through the standard sync policy.

**Sensitive**:
Source content may be used when relevant, but excerpts and duplication should be minimized.

**Restricted**:
Only metadata and references are synchronized by default; content processing requires explicit approval.

**Current-version-only policy**:
Connected-source notes reflect the newest known version. The system keeps the current reference, latest content hash, detection time, and refreshed-note record, but does not retain prior summaries or source text unless explicitly archived.

**Clear-first writing**:
Generated prose should sound natural and understandable to Moksh: direct, reflective when appropriate, and grounded in evidence. Technical terms are explained in plain language, while exact code, filenames, commands, measurements, and quotations are preserved. Formal language is used when the source or deliverable requires it, without making the explanation harder to follow.

**Type-specific template**:
Every canonical note has consistent metadata and a short plain-language summary. The remaining sections depend on the note type so notes contain only the structure that helps their purpose.

### Status language

**Inbox**:
New or uncategorized material awaiting classification.

**Active**:
Work currently being performed.

**Next**:
A defined next action that is not yet being performed.

**Waiting**:
Work paused because it depends on another person, system, or event.

**Blocked**:
Work cannot proceed because of a known obstacle.

**Paused**:
Work intentionally stopped without being abandoned.

**Complete**:
Work finished and validated; the resulting evidence remains accessible.

**Archived**:
Material retained for reference but removed from default active views.

### Boundaries

- Live project directories remain the source of truth for original files.
- The vault preserves provenance and adds curated context; it does not silently delete or rewrite originals.
- The system updates an existing canonical note when it can hold new information clearly before creating a new note.
- Source records are lightweight by default; standalone source notes are created only when they pass the promotion threshold.
- The source registry is centralized in one readable note rather than one file per source.
- Activity is recorded in one central log and filtered for meaningful changes; routine refreshes remain system-health data.
- Meaningful activity is retained indefinitely as compact entries; older entries may be filtered or collapsed.
- Daily automation preserves usage by stopping at its call and token limits and prioritizing high-value changes.
- AI is an optional accelerator; local deterministic behavior remains the fallback and source of system continuity.
- AI is opt-in rather than a hidden dependency of daily synchronization.
- Uncertain or conflicting local classifications go to Inbox with a reason instead of being guessed.
- Categorization rules are versioned and independently editable so the system can scale without code changes.
- Source-registry identity, reference, dates, hashes, authority, coverage, sensitivity, sync status, and promotion status are managed; personal notes and explicit overrides are protected.
- Normal use should require only a clear dashboard and a small number of plain-language actions; advanced system details remain secondary.
- `Refresh` updates changed material locally, `Review` handles ambiguity and decisions, and `Rebuild` runs a larger approved organization pass.
- Rebuild changes are not applied until the preview is accepted; the preview can be narrowed or canceled.
- Branch landing pages are navigation hubs, not inventories that force every artifact into a deep folder tree.
- Migration removes old duplicate navigation only after the new structure and links are verified.
- Status reports are useful first-party evidence but are not assumed to be complete; reconstruction cross-checks them against code, files, Gmail, Drive, datasets, notebooks, deliverables, and notes.
- The graph favors clear hub-and-spoke navigation and meaningful relationships over link density.
- Project and branch indexes are navigation hubs; evidence links must explain or support a note.
- When a connected source changes, canonical notes are updated to the newest known version rather than accumulating historical summaries.
- The seven branches are shared across projects; `project` metadata and project indexes provide project-specific views.
- ByteSmart is the current visible project identity. Bitwise may appear as source or provenance metadata, but Bitwise material is organized inside ByteSmart and does not create a separate project, dashboard, or branch.
- Future projects use their own project metadata, source roots, rules, and project index while sharing the same seven branch model and local automation.
- Automation may update managed sections and metadata, but not protected human-authored sections.
- Protected sections are `Interpretation`, `Decision`, `Next Steps`, `Caveats`, and `Human Notes`.
- New-note intake preserves the note body and never overwrites existing frontmatter without evidence and review.
- Status changes are automatic only when confidence is high and evidence is clear.
- Generated writing avoids corporate language, filler, emojis, and artificial-sounding phrasing; it does not invent details or make evidence stronger than it is.
- Canonical notes use type-specific templates instead of a universal template with unnecessary sections.
