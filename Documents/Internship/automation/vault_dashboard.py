"""Render a compact, local-only health summary in the ByteSmart Command Center."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys

from project_registry import ProjectRegistryError, load_projects


DEFAULT_VAULT = Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault")
DEFAULT_PROJECTS = Path(__file__).with_name("projects.toml")


@dataclass(frozen=True)
class DashboardHealth:
    project_id: str
    local_sources: int
    external_sources: int
    source_review: int
    decision_review: int
    last_refresh: str
    changed: int
    unchanged: int
    active_work: int
    next_work: int
    waiting_work: int
    blocked_work: int
    recent_activity: str


def _table_rows(path: Path, header: str) -> tuple[dict[str, str], ...]:
    if not path.exists():
        return ()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith(header)), None)
    if header_index is None:
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
        if ":" in line:
            key, value = line.split(":", maxsplit=1)
            fields[key.strip()] = value.strip().strip('"')
    return {}


def _work_counts(path: Path) -> dict[str, int]:
    counts = {"active": 0, "next": 0, "waiting": 0, "blocked": 0}
    if not path.exists():
        return counts
    current: str | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            candidate = line[3:].strip().casefold()
            current = candidate if candidate in counts else None
        elif current and line.startswith("- "):
            counts[current] += 1
    return counts


def _section_bullets(path: Path, heading: str) -> int:
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line.strip().casefold() != f"## {heading}".casefold():
            continue
        count = 0
        for candidate in lines[index + 1 :]:
            if candidate.startswith("## "):
                return count
            if candidate.startswith("- "):
                count += 1
        return count
    return 0


def _recent_activity(path: Path, project_title: str) -> str:
    if not path.exists():
        return "No meaningful activity recorded yet."
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for candidate in reversed(lines):
        if candidate.startswith(f"- [{project_title}]"):
            return candidate[2:].strip()
    return "No meaningful activity recorded yet."


def _note_path(vault_root: Path, note_name: str) -> Path:
    path = Path(note_name)
    if path.name != note_name or note_name in {".", ".."}:
        raise ValueError("dashboard and work-queue note names must be single filenames")
    return vault_root / f"{note_name}.md"


def _refresh_state(vault_root: Path, project_id: str) -> tuple[str, int, int]:
    path = vault_root / ".connected-vault" / "refresh-state.json"
    if not path.exists():
        return "Not yet refreshed", 0, 0
    raw = json.loads(path.read_text(encoding="utf-8"))
    project = raw.get("projects", {}).get(project_id, {})
    if not isinstance(project, dict):
        return "Not yet refreshed", 0, 0
    result = project.get("last_result", {})
    if not isinstance(result, dict):
        result = {}
    return str(project.get("refreshed_at", "Not yet refreshed")), int(result.get("changed", 0)), int(result.get("unchanged", 0))


def build_dashboard(
    vault_root: Path,
    project_id: str,
    project_title: str = "ByteSmart",
    dashboard_note: str = "ByteSmart Command Center",
    work_queue_note: str = "Current Internship Work Queue",
) -> DashboardHealth:
    """Collect dashboard health from generated local vault records without model calls."""
    vault_root = vault_root.expanduser().resolve()
    source_rows = _table_rows(vault_root / "Connected Sources" / "Source Registry.md", "| Source ID |")
    rows = tuple(row for row in source_rows if row.get("Source ID", "").startswith(f"{project_id}-"))
    external = tuple(row for row in rows if f"{project_id}-external-" in row.get("Source ID", ""))
    local = tuple(row for row in rows if row not in external)
    pending_decisions = 0
    for path in vault_root.rglob("*.md"):
        metadata = _frontmatter(path)
        if (
            metadata.get("type") == "decision"
            and metadata.get("project") == project_title
            and metadata.get("status", "").casefold() in {"pending", "defer"}
        ):
            pending_decisions += 1
    work = _work_counts(_note_path(vault_root, work_queue_note))
    if work["active"] == 0:
        work["active"] = _section_bullets(_note_path(vault_root, dashboard_note), "Current focus")
    last_refresh, changed, unchanged = _refresh_state(vault_root, project_id)
    return DashboardHealth(
        project_id=project_id,
        local_sources=len(local),
        external_sources=len(external),
        source_review=sum(row.get("Sync") == "Needs review" for row in local),
        decision_review=pending_decisions,
        last_refresh=last_refresh,
        changed=changed,
        unchanged=unchanged,
        active_work=work["active"],
        next_work=work["next"],
        waiting_work=work["waiting"],
        blocked_work=work["blocked"],
        recent_activity=_recent_activity(vault_root / "Current Work" / "Meaningful Activity.md", project_title),
    )


def write_dashboard(
    vault_root: Path,
    health: DashboardHealth,
    dashboard_note: str = "ByteSmart Command Center",
    work_queue_note: str = "Current Internship Work Queue",
) -> Path:
    """Update only the dashboard's managed health block, preserving human content."""
    vault_root = vault_root.expanduser().resolve()
    path = _note_path(vault_root, dashboard_note)
    start = f"<!-- managed:dashboard-health:{health.project_id}:start -->"
    end = f"<!-- managed:dashboard-health:{health.project_id}:end -->"
    lines = [
        start,
        "## Live vault health",
        "",
        "| Signal | Current state |",
        "|---|---|",
        f"| Local sources | {health.local_sources} |",
        f"| Connected-source records | {health.external_sources} |",
        f"| Source review | {health.source_review} |",
        f"| Decision review | {health.decision_review} |",
        f"| Last local refresh | {health.last_refresh} |",
        f"| Changed / skipped | {health.changed} / {health.unchanged} |",
        f"| Active / next work | {health.active_work} / {health.next_work} |",
        f"| Waiting / blocked work | {health.waiting_work} / {health.blocked_work} |",
        "",
        f"Latest activity: {health.recent_activity}",
        "",
        f"→ [[{work_queue_note}]] · [[Meaningful Activity]]",
        "",
        "→ [[Review Queue]] · [[Rebuild Preview]] · [[Automation Guide]]",
        end,
    ]
    generated = "\n".join(lines)
    existing = path.read_text(encoding="utf-8") if path.exists() else f"# {dashboard_note}\n"
    if start in existing and end in existing:
        before, remainder = existing.split(start, 1)
        _, after = remainder.split(end, 1)
        content = before.rstrip() + "\n\n" + generated + after
    else:
        content = existing.rstrip() + "\n\n" + generated + "\n"
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--project", help="project ID; defaults to the active project")
    args = parser.parse_args(argv)
    try:
        registry = load_projects(args.projects)
        project = registry.project(args.project) if args.project else registry.active_project
        dashboard_note = project.dashboard_note or f"{project.title} Command Center"
        work_queue_note = project.work_queue_note or f"{project.title} Work Queue"
        health = build_dashboard(args.vault, project.id, project.title, dashboard_note, work_queue_note)
        path = write_dashboard(args.vault, health, dashboard_note, work_queue_note)
    except (OSError, ValueError, ProjectRegistryError) as error:
        print(f"Dashboard refresh failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"project": project.id, "dashboard": str(path), "source_review": health.source_review}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
