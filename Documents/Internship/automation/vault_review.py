"""Build one local review queue from the current source registry and pending decisions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys

from project_registry import Project, ProjectRegistryError, load_projects


DEFAULT_VAULT = Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault")
DEFAULT_PROJECTS = Path(__file__).with_name("projects.toml")
PENDING_DECISION_STATUSES = frozenset({"pending", "defer"})
PROTECTED_HEADINGS = frozenset({"Interpretation", "Decision", "Next Steps", "Caveats", "Human Notes"})


@dataclass(frozen=True)
class SourceReviewItem:
    source_id: str
    title: str
    branch: str
    reference: str
    reason: str


@dataclass(frozen=True)
class DecisionReviewItem:
    title: str
    status: str
    reference: str


@dataclass(frozen=True)
class ReviewItems:
    source_items: tuple[SourceReviewItem, ...]
    decision_items: tuple[DecisionReviewItem, ...]


def _table_rows(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists():
        return ()
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("| Source ID |")), None)
    if header_index is None or header_index + 1 >= len(lines):
        return ()
    headers = [cell.strip() for cell in lines[header_index].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("| "):
            break
        values = [cell.strip().replace("\\|", "|") for cell in line.strip("|").split("|")]
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values, strict=True)))
    return tuple(rows)


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        fields[key.strip()] = value.strip().strip('"')
    return {}


def _pending_decisions(vault_root: Path, project: Project) -> tuple[DecisionReviewItem, ...]:
    decisions: list[DecisionReviewItem] = []
    for path in sorted(vault_root.rglob("*.md")):
        metadata = _frontmatter(path)
        if metadata.get("type") != "decision" or metadata.get("project") != project.title:
            continue
        status = metadata.get("status", "").casefold()
        if status not in PENDING_DECISION_STATUSES:
            continue
        decisions.append(
            DecisionReviewItem(
                title=path.stem,
                status=status,
                reference=str(path),
            )
        )
    return tuple(decisions)


def collect_review_items(vault_root: Path, project: Project) -> ReviewItems:
    """Collect unresolved local classifications and explicitly pending decisions."""
    vault_root = vault_root.expanduser().resolve()
    registry = vault_root / "Connected Sources" / "Source Registry.md"
    source_items = tuple(
        SourceReviewItem(
            source_id=row["Source ID"],
            title=row["Title"],
            branch=row["Branch"],
            reference=row["Reference"],
            reason=row.get("Review reason", "needs human review"),
        )
        for row in _table_rows(registry)
        if row.get("Sync") == "Needs review" and row.get("Source ID", "").startswith(f"{project.id}-")
    )
    return ReviewItems(source_items=source_items, decision_items=_pending_decisions(vault_root, project))


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _protected_sections(content: str) -> tuple[str, ...]:
    lines = content.splitlines()
    sections: list[str] = []
    start: int | None = None
    for index, line in enumerate(lines):
        heading = line[3:].strip() if line.startswith("## ") else None
        if heading in PROTECTED_HEADINGS:
            if start is not None:
                sections.append("\n".join(lines[start:index]).strip())
            start = index
        elif start is not None and line.startswith("## "):
            sections.append("\n".join(lines[start:index]).strip())
            start = None
    if start is not None:
        sections.append("\n".join(lines[start:]).strip())
    return tuple(section for section in sections if section)


def write_review_queue(vault_root: Path, project: Project, items: ReviewItems) -> Path:
    """Write one concise Review queue; individual review items do not become notes."""
    queue_path = vault_root / "Findings & Decisions" / "Review Queue.md"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Review Queue — {project.title}",
        "",
        f"This section holds only {project.title} items that need a human decision. Review each item, then add its exact registry reference to `automation/{project.id}_vault_overrides.toml` when the choice should stay consistent.",
        "",
        "## Source review",
        "",
    ]
    if items.source_items:
        lines.extend(
            [
                "| Source | Current placement | Reason | Reference |",
                "|---|---|---|---|",
                *[
                    "| " + " | ".join(_cell(value) for value in (item.title, item.branch, item.reason, item.reference)) + " |"
                    for item in items.source_items
                ],
            ]
        )
    else:
        lines.append("No source classifications need review.")
    lines.extend(["", "## Decision review", ""])
    if items.decision_items:
        lines.extend(
            [
                "| Decision | Status | Reference |",
                "|---|---|---|",
                *[
                    "| " + " | ".join(_cell(value) for value in (item.title, item.status, item.reference)) + " |"
                    for item in items.decision_items
                ],
            ]
        )
    else:
        lines.append("No decisions are waiting for a choice.")
    managed_start = f"<!-- managed:review-queue:{project.id}:start -->"
    managed_end = f"<!-- managed:review-queue:{project.id}:end -->"
    generated_body = "\n".join(lines)
    managed_content = f"{managed_start}\n{generated_body}\n{managed_end}\n"
    if not queue_path.exists():
        content = (
            "---\n"
            "type: index\n"
            "project: Shared\n"
            "branch: Findings & Decisions\n"
            "status: Active\n"
            "confidence: high\n"
            "review: false\n"
            "---\n\n"
            + managed_content
        )
    else:
        existing = queue_path.read_text(encoding="utf-8")
        start = existing.find(managed_start)
        end = existing.find(managed_end)
        if start >= 0 and end >= start:
            prior_managed_content = existing[start + len(managed_start) : end]
            protected = _protected_sections(prior_managed_content)
            if protected:
                generated_body += "\n\n" + "\n\n".join(protected)
            managed_content = f"{managed_start}\n{generated_body}\n{managed_end}\n"
            content = existing[:start] + managed_content + existing[end + len(managed_end) :].lstrip("\n")
        else:
            content = existing.rstrip() + "\n\n" + managed_content
    if not queue_path.exists() or queue_path.read_text(encoding="utf-8") != content:
        queue_path.write_text(content, encoding="utf-8")
    return queue_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--project", help="project ID; defaults to the active project")
    args = parser.parse_args(argv)
    try:
        registry = load_projects(args.projects)
        project = registry.project(args.project) if args.project else registry.active_project
        items = collect_review_items(args.vault, project)
        queue_path = write_review_queue(args.vault, project, items)
    except (OSError, ValueError, ProjectRegistryError) as error:
        print(f"Review failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "source_review": len(items.source_items),
                "decision_review": len(items.decision_items),
                "project": project.id,
                "queue": str(queue_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
