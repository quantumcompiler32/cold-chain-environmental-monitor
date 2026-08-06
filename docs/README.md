# Documentation map

This folder contains the project documentation. Start with the root
[`README.md`](../README.md) for installation and the required startup order.

| Topic | File |
| --- | --- |
| System architecture and pipeline | [`architecture-and-pipeline.md`](architecture-and-pipeline.md) |
| Database read/write ownership | [`database-access.md`](database-access.md) |
| Event fields and status definitions | [`data-dictionary.md`](data-dictionary.md) |
| Setup, startup, shutdown, and restart | [`MD Files for Running/setup-and-runbook.md`](MD%20Files%20for%20Running/setup-and-runbook.md) |
| Terminal-only operator workflow | [`MD Files for Running/terminal-runbook.md`](MD%20Files%20for%20Running/terminal-runbook.md) |
| Troubleshooting | [`MD Files for Running/troubleshooting.md`](MD%20Files%20for%20Running/troubleshooting.md) |

The remaining documents are operational checklists for demonstrations and
presentation handoff. They are not separate application implementations.

## Research and supporting materials

- Research papers and source notes are in `research/`.
- Source URLs are in `research/research_urls.doc`.
- PowerPoint and Google Slides access notes are in `presentation/`.
- Dataset notes are in `datasets/`; the canonical 61 MB CSV remains in
  `ai_worker/data/` so the trainer and event generator do not duplicate it.
- Project lessons are in `lessons/`, with shared styling in `assets/`.
- Engineering learning records are in `learning-records/`.
- Repository source links are collected in `RESOURCES.md`.
