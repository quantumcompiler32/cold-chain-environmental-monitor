"""Preview or apply a safe reorganization of existing vault artifact copies."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import sys

from project_registry import ProjectRegistryError, load_projects


DEFAULT_VAULT = Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault")
DEFAULT_PROJECTS = Path(__file__).with_name("projects.toml")
BRANCHES = frozenset(
    {
        "Current Work",
        "Connected Sources",
        "System & Sensors",
        "Data Pipeline & Storage",
        "Analysis & Models",
        "Findings & Decisions",
        "Deliverables & Visuals",
    }
)


@dataclass(frozen=True)
class MoveProposal:
    source: Path
    destination: Path
    branch: str
    inbound_notes: tuple[Path, ...] = ()


@dataclass(frozen=True)
class RebuildPlan:
    project_id: str
    moves: tuple[MoveProposal, ...]
    linked_candidates: tuple[MoveProposal, ...]
    review_items: int


def _registry_rows(path: Path) -> tuple[dict[str, str], ...]:
    if not path.exists():
        return ()
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("| Source ID |")), None)
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


def _linked_artifacts(vault_root: Path, artifacts: Path) -> dict[Path, tuple[Path, ...]]:
    """Return artifact copies referenced by another Markdown note in the vault."""
    linked: dict[Path, list[Path]] = {}
    artifact_paths = tuple(path for path in artifacts.rglob("*") if path.is_file())
    for note in vault_root.rglob("*.md"):
        if artifacts in note.parents:
            continue
        content = note.read_text(encoding="utf-8", errors="replace")
        for artifact in artifact_paths:
            relative = artifact.relative_to(vault_root).as_posix()
            if f"[[{relative}" in content:
                linked.setdefault(artifact, []).append(note)
    return {artifact: tuple(notes) for artifact, notes in linked.items()}


def build_plan(vault_root: Path, project_id: str) -> RebuildPlan:
    """Propose moves of vault copies only; live source paths are never candidates."""
    vault_root = vault_root.expanduser().resolve()
    rows = _registry_rows(vault_root / "Connected Sources" / "Source Registry.md")
    branch_candidates: dict[str, set[str]] = {}
    for row in rows:
        if not row.get("Source ID", "").startswith(f"{project_id}-") or row.get("Branch") not in BRANCHES:
            continue
        branch_candidates.setdefault(row["Title"], set()).add(row["Branch"])
    branches_by_title = {
        title: next(iter(branches))
        for title, branches in branch_candidates.items()
        if len(branches) == 1
    }
    review_items = sum(
        row.get("Sync") == "Needs review" and row.get("Source ID", "").startswith(f"{project_id}-") for row in rows
    )
    moves: list[MoveProposal] = []
    linked_candidates: list[MoveProposal] = []
    artifacts = vault_root / "Artifacts"
    if artifacts.exists():
        linked_artifacts = _linked_artifacts(vault_root, artifacts)
        for artifact in sorted(path for path in artifacts.rglob("*") if path.is_file()):
            branch = branches_by_title.get(artifact.name)
            if not branch:
                continue
            destination = vault_root / branch / "Reference" / artifact.name
            if destination.exists() or artifact == destination:
                continue
            proposal = MoveProposal(
                source=artifact,
                destination=destination,
                branch=branch,
                inbound_notes=linked_artifacts.get(artifact, ()),
            )
            if proposal.inbound_notes:
                linked_candidates.append(proposal)
            else:
                moves.append(proposal)
    return RebuildPlan(
        project_id=project_id,
        moves=tuple(moves),
        linked_candidates=tuple(linked_candidates),
        review_items=review_items,
    )


def apply_plan(plan: RebuildPlan, *, confirm: bool) -> None:
    """Move only proposed vault copies after the caller has explicitly confirmed."""
    if not confirm:
        raise ValueError("rebuild apply requires explicit confirmation")
    for proposal in plan.moves:
        if not proposal.source.is_file():
            raise FileNotFoundError(f"artifact copy no longer exists: {proposal.source}")
        if proposal.destination.exists():
            raise FileExistsError(f"rebuild destination already exists: {proposal.destination}")
    moved: list[MoveProposal] = []
    try:
        for proposal in plan.moves:
            proposal.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(proposal.source), str(proposal.destination))
            moved.append(proposal)
    except OSError:
        for proposal in reversed(moved):
            if proposal.destination.exists() and not proposal.source.exists():
                shutil.move(str(proposal.destination), str(proposal.source))
        raise


def write_preview(vault_root: Path, plan: RebuildPlan) -> Path:
    vault_root = vault_root.expanduser().resolve()
    preview = vault_root / "Findings & Decisions" / "Rebuild Preview.md"
    preview.parent.mkdir(parents=True, exist_ok=True)
    marker_start = f"<!-- managed:rebuild-preview:{plan.project_id}:start -->"
    marker_end = f"<!-- managed:rebuild-preview:{plan.project_id}:end -->"
    display = lambda path: f"`{path.relative_to(vault_root).as_posix()}`"
    lines = [
        marker_start,
        f"## Rebuild Preview — {plan.project_id}",
        "",
        "This is a preview only. No source file, protected note content, or vault copy changes until an explicit apply command is confirmed.",
        "",
        "## Proposed vault-copy moves",
        "",
    ]
    if plan.moves:
        lines.extend(["| From | To | Branch |", "|---|---|---|"])
        lines.extend(f"| {display(move.source)} | {display(move.destination)} | {move.branch} |" for move in plan.moves)
    else:
        lines.append("No safe vault-copy moves are currently proposed.")
    lines.extend(
        [
            "",
            "## Linked copies requiring manual migration",
            "",
        ]
    )
    if plan.linked_candidates:
        lines.extend(["| From | Proposed destination | Referencing notes |", "|---|---|---|"])
        for move in plan.linked_candidates:
            notes = ", ".join(f"[[{note.stem}]]" for note in move.inbound_notes)
            lines.append(f"| {display(move.source)} | {display(move.destination)} | {notes} |")
    else:
        lines.append("No linked vault copies need manual migration.")
    lines.extend(
        [
            "",
            "## Review items",
            "",
            f"{plan.review_items} items remain in Review and will not move automatically.",
            "",
            "## Protected notes left untouched",
            "",
            "All protected human-authored sections and live source files are outside this plan.",
            "",
            "## Notes changed by automatic apply",
            "",
            "None. Linked copies are excluded from automatic moves and listed above for manual migration.",
            "",
            marker_end,
        ]
    )
    generated = "\n".join(lines)
    if preview.exists():
        existing = preview.read_text(encoding="utf-8")
        if marker_start in existing and marker_end in existing:
            before, remainder = existing.split(marker_start, 1)
            _, after = remainder.split(marker_end, 1)
            content = before.rstrip() + "\n\n" + generated + after
        else:
            content = existing.rstrip() + "\n\n" + generated + "\n"
    else:
        content = "\n".join(
            [
                "---",
                "type: review",
                "project: Shared",
                "branch: Findings & Decisions",
                "status: Pending",
                "confidence: high",
                "review: true",
                "---",
                "",
                "# Rebuild Preview",
                "",
                generated,
                "",
                "## Human Notes",
                "",
                "Add decisions or exceptions here; rebuild updates preserve this section.",
            ]
        )
    preview.write_text(content.rstrip() + "\n", encoding="utf-8")
    return preview


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--project", help="project ID; defaults to the active project")
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--only", action="append", default=[], help="artifact-copy path relative to Artifacts; may be repeated")
    args = parser.parse_args(argv)
    try:
        registry = load_projects(args.projects)
        project = registry.project(args.project) if args.project else registry.active_project
        plan = build_plan(args.vault, project.id)
        if args.only:
            requested = {Path(value).as_posix() for value in args.only}
            artifact_root = args.vault.expanduser().resolve() / "Artifacts"
            plan = RebuildPlan(
                project_id=plan.project_id,
                moves=tuple(move for move in plan.moves if move.source.relative_to(artifact_root).as_posix() in requested),
                linked_candidates=tuple(
                    move for move in plan.linked_candidates if move.source.relative_to(artifact_root).as_posix() in requested
                ),
                review_items=plan.review_items,
            )
        if args.apply:
            apply_plan(plan, confirm=args.confirm)
        preview_path = write_preview(args.vault, plan) if args.write_preview else None
    except (OSError, ValueError, ProjectRegistryError) as error:
        print(f"Rebuild failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"project": project.id, "moves": len(plan.moves), "review": plan.review_items, "preview": str(preview_path) if preview_path else None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
