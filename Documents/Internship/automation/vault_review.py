"""Build one local review queue from the current source registry and pending decisions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys


DEFAULT_VAULT = Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault")
PENDING_DECISION_STATUSES = frozenset({"pending", "defer"})


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


def _pending_decisions(vault_root: Path) -> tuple[DecisionReviewItem, ...]:
    decisions: list[DecisionReviewItem] = []
    for path in sorted(vault_root.rglob("*.md")):
        metadata = _frontmatter(path)
        if metadata.get("type") != "decision":
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


def collect_review_items(vault_root: Path) -> ReviewItems:
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
        if row.get("Sync") == "Needs review"
    )
    return ReviewItems(source_items=source_items, decision_items=_pending_decisions(vault_root))


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def write_review_queue(vault_root: Path, items: ReviewItems) -> Path:
    """Write one concise Review queue; individual review items do not become notes."""
    queue_path = vault_root / "Findings & Decisions" / "Review Queue.md"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "type: index",
        "project: ByteSmart",
        "branch: Findings & Decisions",
        "status: Active",
        "confidence: high",
        "review: false",
        "cssclasses:",
        "  - bytesmart-branch",
        "  - branch-findings-decisions",
        "---",
        "",
        "# Review Queue",
        "",
        "This page holds only items that need a human decision. Review each item, then add a rule or override when the choice should stay consistent.",
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
    content = "\n".join(lines) + "\n"
    if not queue_path.exists() or queue_path.read_text(encoding="utf-8") != content:
        queue_path.write_text(content, encoding="utf-8")
    return queue_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    args = parser.parse_args(argv)
    try:
        items = collect_review_items(args.vault)
        queue_path = write_review_queue(args.vault, items)
    except (OSError, ValueError) as error:
        print(f"Review failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "source_review": len(items.source_items),
                "decision_review": len(items.decision_items),
                "queue": str(queue_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
