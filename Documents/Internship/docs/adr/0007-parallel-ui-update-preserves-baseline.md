---
status: accepted
---

# Build the Phase 1 UI update beside the baseline dashboard

The supplied Stitch design reference will first be implemented as a local integrated prototype in a separate dashboard directory rather than replacing the existing dashboard. Phase 1 covers Operations, Raw Events, and Interpretation/Methodology; the Summary/Impact view is intentionally deferred to Phase 2. This preserves existing features while allowing the design reference to be populated with current repository-backed facts before any later GitHub integration.

## Consequences

- The baseline dashboard remains available and unchanged as a runnable reference.
- Phase 1 needs separate entry points or assets so its UI changes cannot disable baseline behavior.
- The Stitch content is treated as presentation guidance; current repository data and behavior remain authoritative.
- Impact-specific claims and presentation are postponed until Phase 2.
