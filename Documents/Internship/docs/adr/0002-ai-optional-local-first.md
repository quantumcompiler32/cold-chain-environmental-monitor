---
status: accepted
---

# Keep vault automation AI-optional and local-first

The vault must remain useful when AI is unavailable, disabled, or out of usage. Local deterministic logic owns file discovery, change detection, hashes, metadata, source-registry updates, rule-based categorization, indexes, dashboard state, explicit status changes, audits, activity logging, and review queues. AI is an optional accelerator for summaries, semantic classification, ambiguity resolution, and clear-first rewriting; an unavailable model leaves work in Review rather than blocking synchronization.

## Consequences

- The vault can continue organizing and exposing work without model calls.
- AI usage is reserved for tasks where it adds meaningful value.
- Rule-based behavior must be understandable and testable.
- AI-dependent suggestions need an explicit unavailable or needs-review state.
