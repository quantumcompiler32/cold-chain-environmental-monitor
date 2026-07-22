# Internship Context And Glossary

## Canonical terms

- **ByteSmart** — the main project for environmental and cold-chain monitoring, analysis, and related learning artifacts.
- **Bitwise** — material and reporting context included within ByteSmart; it is not a separate project or navigation layer.
- **Reading** — one timestamped measurement from a dataset or sensor stream.
- **Event** — a JSON representation of a reading published through MQTT and persisted by the database listener.
- **Excursion** — a reading or period outside a configured temperature range; it is an investigation signal, not a product-release decision.
- **Relatively warm** — a project-defined analytical label, not a clinical or regulatory conclusion.
- **Stable** — a project-defined pattern of readings that remains within the selected analysis boundaries.
- **Needs investigation** — a project status indicating that the data deserves review by a qualified person.
- **K-Means** — an exploratory clustering method that groups patterns; it does not prove that a real failure occurred.
- **Model label** — a derived training target that must be created without leaking the answer into the features.
- **Canonical note** — a durable, current-first curated explanation linked to its evidence; it is not a copy of every source artifact or a history of every prior summary.
- **Source record** — a provenance entry for a local, Gmail, Google Drive, dataset, or reference source.
- **Coverage** — how much relevant work a source captures: `Complete`, `Partial`, or `Unknown`; it is separate from authority.
- **Promotion threshold** — the rule that a source becomes a standalone canonical note only when it adds durable value for retrieval, execution, analysis, a decision, or provenance.
- **Curated graph** — a deliberately limited set of useful links between indexes, canonical notes, work, evidence, findings, decisions, and deliverables.
- **Source registry** — one readable Markdown note containing source records; a source receives its own note only when it passes the promotion threshold.
- **Meaningful activity** — a change that affects work, blockers, decisions, deliverables, sources, findings, or automation reliability.
- **Activity retention** — meaningful activity stays in the central log as compact entries and may be filtered or collapsed without being removed.
- **Daily automation budget** — the daily refresh stops at 10 model calls, 25,000 input tokens, or 5,000 output tokens, and queues remaining work.
- **AI-optional automation** — core vault behavior works locally; AI adds higher-level summaries, semantic classification, ambiguity resolution, and rewriting without becoming a dependency.
- **AI opt-in** — daily refreshes run locally by default; AI is enabled only for a specific task or an approved on-demand run.
- **Deterministic categorization** — local rules classify using explicit metadata, placement, paths, filenames, headings, extensions, and known ByteSmart terms without inventing meaning.
- **Categorization rules** — human-readable, validated mappings used by local classification; explicit note metadata takes priority.
- **Explicit override** — a manual correction to an automation-managed value that remains in effect until removed or changed.
- **Simple-by-default use** — the vault exposes a small set of understandable actions while keeping technical automation details secondary.
- **Primary actions** — the normal dashboard's three actions: `Refresh`, `Review`, and `Rebuild`.
- **Rebuild preview** — the proposed-change and usage estimate shown before a larger organization pass is applied.
- **Shallow navigation** — one landing page per branch with only useful subfolders; detail is connected through links, metadata, and search.
- **Preserve-first migration** — reorganize vault material while leaving original source files untouched; unclear items remain accessible until the new structure is verified.
- **Managed section** — a clearly marked note section that automation may update while protected human-authored sections remain unchanged.
- **Protected sections** — `Interpretation`, `Decision`, `Next Steps`, `Caveats`, and `Human Notes`; automation does not rewrite these sections.
- **Review queue** — the holding area for ambiguous classifications, contradictions, low-confidence changes, and unresolved questions.
- **Decision queue** — the dashboard view of choices awaiting an explicit `approved`, `rejected`, or `defer` decision.
- **Defer** — intentionally leave a decision open without applying the proposed change yet.
- **Daily refresh** — an incremental synchronization based on file events, metadata, hashes, and diffs before any model call.
- **On-demand sync** — a user-triggered synchronization scoped to selected files, projects, branches, or a requested rebuild.
- **New-note intake** — content-preserving handling for notes without metadata; high-confidence notes receive metadata and placement, while ambiguous notes go to Inbox.
- **High-confidence automation** — an evidence-backed change that can be applied without approval; uncertain changes go to Review.
- **Sensitivity level** — a source-handling classification with three values: `Normal`, `Sensitive`, or `Restricted`.
- **Normal** — source content may be summarized and linked through the standard sync policy.
- **Sensitive** — relevant content may be used, but excerpts and duplication should be minimized.
- **Restricted** — only metadata and references are synchronized by default; content processing requires explicit approval.
- **Current-version-only policy** — connected-source notes reflect the newest known version; only minimal audit metadata is retained unless an archive is explicitly requested.
- **Clear-first writing** — generated notes use plain, natural language, explain technical terms, preserve evidence, and use formal language only when the source or deliverable requires it.
- **Type-specific template** — every canonical note shares metadata and a short summary, while the remaining sections depend on its note type.

## Boundaries

- Hobby-grade sensors and a cooler experiment cannot replace certified vaccine-monitoring equipment.
- Air temperature is not automatically equivalent to product temperature.
- ML output supports exploration and explanation; it does not authorize medical, safety, potency, use, or discard decisions.

## Related notes

- [[ByteSmart Project]]
- [[Bitwise Internship Timeline]]
- [[Vault Design Decisions]]
