---
type: decision
project: Shared
branch: Findings & Decisions
status: Active
source: [[Internship Context And Glossary]]
created: 2026-07-21
updated: 2026-07-21
confidence: high
review: false
---

# Vault Design Decisions

This note records the agreed design for the reusable connected-project vault. It is intentionally separate from implementation details.

→ [[ByteSmart Vault Specification]]

## Agreed structure

- One vault begins with ByteSmart and can expand to future projects without introducing a second automation system.
- Bitwise-related material is included within ByteSmart and may appear as provenance metadata; it is not a separate project, dashboard, or branch.
- Future projects receive their own metadata, source roots, rules, and project index while sharing the seven branches and the same local-first refresh system.
- Seven shared branches:
  - [[Current Work]]
  - [[Connected Sources]]
  - [[System & Sensors]]
  - [[Data Pipeline & Storage]]
  - [[Analysis & Models]]
  - [[Findings & Decisions]]
  - [[Deliverables & Visuals]]
- Project indexes provide project-specific views without duplicating notes.
- The live project directory remains authoritative for original files.
- Canonical notes reflect the newest known source version rather than accumulating historical summaries.
- Source updates retain only the current reference, latest hash, detection time, and refreshed-note record by default.

## Agreed automation boundary

- Daily refresh is incremental and begins with local metadata, hashes, events, and diffs.
- On-demand sync can target a file, project, branch, or full rebuild.
- High-confidence classifications and status changes may be applied automatically.
- Ambiguous or contradictory changes go to Review or the Decision queue.
- Managed sections and metadata may be updated automatically.
- Human-authored interpretation, decisions, notes, and next steps remain protected.
- Protected headings are `Interpretation`, `Decision`, `Next Steps`, `Caveats`, and `Human Notes`; existing unmarked content is protected by default.
- Originals are never silently deleted or rewritten.
- New notes preserve their body; high-confidence intake may add metadata and placement, while ambiguous items go to Inbox.
- The vault favors updating an existing note over creating a duplicate.
- Source records remain lightweight by default; standalone notes require a useful contribution under the promotion threshold.
- The source registry is one readable Markdown note rather than one file per source.
- Activity uses one central log and records only meaningful changes; routine refreshes update system health without creating daily notes.
- Meaningful activity is retained indefinitely as compact entries and may be filtered or collapsed when old.
- The daily refresh makes no calls when unchanged, then stops at 10 model calls, 25,000 input tokens, or 5,000 output tokens to preserve usage.
- Core synchronization, organization, indexing, auditing, dashboards, and queues work without AI; AI is an optional accelerator for higher-level interpretation and rewriting.
- Daily refreshes run locally by default; AI is opt-in for specific tasks or approved on-demand runs.
- Local-only categorization uses explicit metadata and deterministic file signals; uncertain items go to Inbox with a reason.
- Categorization rules are human-readable, validated, versioned, and independent from the automation code.
- Source-registry fields are split between managed values and protected notes; manual corrections are explicit overrides that survive synchronization.
- Normal use presents a clear dashboard and a small number of plain-language actions; advanced controls remain available but secondary.
- The normal dashboard exposes three primary actions: `Refresh`, `Review`, and `Rebuild`.
- Rebuild is preview-first and can be narrowed or canceled before changes are applied.
- Each branch uses a landing page and shallow, purposeful folders instead of a deep folder tree.
- Migration preserves original sources, reorganizes useful vault material, and keeps unclear items in one archive or unclassified area until verification.
- Status reports are evidence, not an exhaustive ledger; reconstruction cross-checks them against project files, code, Gmail, Drive, datasets, notebooks, deliverables, and notes.
- Generated text follows a clear-first style: understandable, direct, evidence-grounded, and natural. Formal language is preserved where required, but technical terms are explained and unnecessary decoration is avoided.
- Canonical notes share metadata and a short summary, then use type-specific sections so irrelevant content is not generated.
- The graph is curated and minimal: indexes act as navigation hubs, and notes link only to evidence or related work that materially helps understanding or action.

## Open decisions

- Exact daily token and request budgets.
- The final source-registry fields and authority scale.
- The final note templates and managed-section markers.
- The implementation mechanism for the dashboard decision controls.
- `defer` means leaving a decision open without applying the proposed change.
