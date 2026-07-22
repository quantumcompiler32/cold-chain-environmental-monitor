"""Refresh one project into a current, local-only Obsidian source registry."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterator
import tomllib

from internship_organizer import is_ignored
from project_registry import Project, ProjectRegistryError, load_projects
from vault_rules import Classification, RuleValidationError, VaultOverrides, VaultRules, classify, load_overrides, load_rules


STATE_VERSION = 1
STATE_DIRECTORY = ".connected-vault"
DEFAULT_PROJECTS = Path(__file__).with_name("projects.toml")
DEFAULT_VAULT = Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault")


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    source_type: str
    branch: str
    reference: str
    authority: str
    coverage: str
    sensitivity: str
    checked_at: str
    content_hash: str
    sync_status: str
    promotion_status: str
    review_reason: str


@dataclass(frozen=True)
class RefreshResult:
    scanned: int
    external: int
    new: int
    changed: int
    unchanged: int
    review: int
    registry_path: Path
    activity_path: Path


def _state_path(vault_root: Path) -> Path:
    return vault_root / STATE_DIRECTORY / "refresh-state.json"


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": STATE_VERSION, "projects": {}}
    with path.open(encoding="utf-8") as state_file:
        state = json.load(state_file)
    if state.get("version") != STATE_VERSION or not isinstance(state.get("projects"), dict):
        raise ValueError(f"unsupported refresh state at {path}")
    return state


def _save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_source_files(project: Project) -> Iterator[tuple[Path, Path]]:
    seen: set[Path] = set()
    for root in project.source_roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"source root does not exist: {root}")
        for path in sorted(root.rglob("*")):
            if path.is_file() and not is_ignored(path, root):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield root, resolved


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _markdown_context(path: Path) -> tuple[str | None, str | None, tuple[str, ...]]:
    if path.suffix.lower() != ".md":
        return None, None, ()
    with path.open(encoding="utf-8", errors="replace") as source_file:
        content = source_file.read(64 * 1024)
    lines = content.splitlines()
    branch = None
    note_type = None
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if ":" not in line:
                continue
            key, value = line.split(":", maxsplit=1)
            value = value.strip().strip('"')
            if key.strip() == "branch":
                branch = value
            elif key.strip() == "type":
                note_type = value
    headings = tuple(line.lstrip("#").strip() for line in lines if line.startswith("#"))
    return branch, note_type, headings


def _source_id(project: Project, root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    digest = hashlib.sha256(f"{project.id}:{root.as_posix()}:{relative}".encode("utf-8")).hexdigest()[:12]
    return f"{project.id}-{digest}"


def _source_type(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "file"


def _external_value(raw: dict[str, object], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"external source {field} must be a non-empty string")
    return value.strip()


def load_external_sources(path: Path, project_id: str) -> tuple[SourceRecord, ...]:
    """Load metadata-only Gmail and Drive references without fetching their content."""
    if not path.exists():
        return ()
    with path.open("rb") as source_file:
        raw = tomllib.load(source_file)
    if raw.get("version") != 1:
        raise ValueError("external source configuration must use version 1")
    entries = raw.get("source", [])
    if not isinstance(entries, list):
        raise ValueError("external source configuration must contain source tables")
    records: list[SourceRecord] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("project") != project_id:
            continue
        identifier = _external_value(entry, "id")
        branch = _external_value(entry, "branch")
        records.append(
            SourceRecord(
                source_id=f"{project_id}-external-{identifier}",
                title=_external_value(entry, "title"),
                source_type=_external_value(entry, "source_type"),
                branch=branch,
                reference=_external_value(entry, "reference"),
                authority=_external_value(entry, "authority"),
                coverage=_external_value(entry, "coverage"),
                sensitivity=_external_value(entry, "sensitivity"),
                checked_at=_external_value(entry, "checked_at"),
                content_hash="metadata-only",
                sync_status=_external_value(entry, "sync_status"),
                promotion_status=_external_value(entry, "promotion_status"),
                review_reason="—",
            )
        )
    if len({record.source_id for record in records}) != len(records):
        raise ValueError(f"external source IDs must be unique for project: {project_id}")
    return tuple(records)


def _record_from(
    project: Project,
    root: Path,
    path: Path,
    classification: Classification,
    content_hash: str,
    checked_at: str,
) -> SourceRecord:
    is_review = classification.is_inbox
    return SourceRecord(
        source_id=_source_id(project, root, path),
        title=path.name,
        source_type=_source_type(path),
        branch=classification.branch or "Inbox",
        reference=str(path),
        authority="Primary",
        coverage="Unknown",
        sensitivity="Normal",
        checked_at=checked_at,
        content_hash=content_hash[:12],
        sync_status="Needs review" if is_review else "Current",
        promotion_status="Review" if is_review else ("Manual override" if classification.reason == "manual override" else "Registry only"),
        review_reason=classification.reason if is_review else "—",
    )


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _existing_registry_records(path: Path) -> tuple[SourceRecord, ...]:
    """Read the generated registry rows so one project's refresh preserves the others."""
    if not path.exists():
        return ()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("| Source ID |")), None)
    if header_index is None:
        return ()
    headers = [cell.strip() for cell in lines[header_index].strip("|").split("|")]
    records: list[SourceRecord] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("| "):
            break
        values = [cell.strip().replace("\\|", "|") for cell in line.strip("|").split("|")]
        if len(values) != len(headers):
            continue
        row = dict(zip(headers, values, strict=True))
        records.append(
            SourceRecord(
                source_id=row["Source ID"],
                title=row["Title"],
                source_type=row["Type"],
                branch=row["Branch"],
                reference=row["Reference"],
                authority=row["Authority"],
                coverage=row["Coverage"],
                sensitivity=row["Sensitivity"],
                checked_at=row["Last checked"],
                content_hash=row["Hash"],
                sync_status=row["Sync"],
                promotion_status=row["Promotion"],
                review_reason=row["Review reason"],
            )
        )
    return tuple(records)


def _write_registry(vault_root: Path, project: Project, records: list[SourceRecord]) -> Path:
    registry_path = vault_root / "Connected Sources" / "Source Registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    preserved = tuple(
        record for record in _existing_registry_records(registry_path) if not record.source_id.startswith(f"{project.id}-")
    )
    all_records = (*preserved, *records)
    lines = [
        "---",
        "type: index",
        "project: Shared",
        "branch: Connected Sources",
        "status: Active",
        "confidence: high",
        "review: false",
        "---",
        "",
        "# Source Registry",
        "",
        "## What this is",
        "",
        "This is the current local record of connected project sources. It helps you trace useful information without copying every source into a separate note.",
        "",
        "| Source ID | Title | Type | Branch | Reference | Authority | Coverage | Sensitivity | Last checked | Hash | Sync | Promotion | Review reason |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for record in sorted(all_records, key=lambda item: (item.source_id.split("-", 1)[0], item.branch, item.title.lower(), item.reference)):
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    record.source_id,
                    record.title,
                    record.source_type,
                    record.branch,
                    record.reference,
                    record.authority,
                    record.coverage,
                    record.sensitivity,
                    record.checked_at,
                    record.content_hash,
                    record.sync_status,
                    record.promotion_status,
                    record.review_reason,
                )
            )
            + " |"
        )
    content = "\n".join(lines) + "\n"
    if not registry_path.exists() or registry_path.read_text(encoding="utf-8") != content:
        registry_path.write_text(content, encoding="utf-8")
    return registry_path


def _write_activity(vault_root: Path, project: Project, result: RefreshResult) -> Path:
    activity_path = vault_root / "Current Work" / "Meaningful Activity.md"
    if result.new == 0 and result.changed == 0:
        return activity_path
    activity_path.parent.mkdir(parents=True, exist_ok=True)
    if not activity_path.exists():
        activity_path.write_text(
            "---\n"
            "type: index\n"
            "project: Shared\n"
            "branch: Current Work\n"
            "status: Active\n"
            "confidence: high\n"
            "review: false\n"
            "---\n\n"
            "# Meaningful Activity\n\n"
            "This log keeps meaningful connected-project changes. Routine unchanged refreshes are left out.\n",
            encoding="utf-8",
        )
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    source_label = "source" if result.scanned == 1 else "sources"
    with activity_path.open("a", encoding="utf-8") as activity_file:
        activity_file.write(
            f"\n## {timestamp}\n\n"
            f"- [{project.title}] Indexed {result.scanned} {source_label}: {result.new} new, {result.changed} changed, {result.review} needs review.\n"
        )
    return activity_path


def refresh_project(
    project: Project,
    rules: VaultRules,
    vault_root: Path,
    external_sources: tuple[SourceRecord, ...] = (),
    overrides: VaultOverrides | None = None,
) -> RefreshResult:
    """Refresh one project using only local files, rules, hashes, and Markdown output."""
    vault_root = vault_root.expanduser().resolve()
    state_path = _state_path(vault_root)
    state = _load_state(state_path)
    projects = state["projects"]
    if not isinstance(projects, dict):
        raise ValueError("refresh state has invalid projects")
    project_state = projects.setdefault(project.id, {"files": {}})
    if not isinstance(project_state, dict):
        raise ValueError(f"refresh state has invalid project: {project.id}")
    previous_files = project_state.setdefault("files", {})
    if not isinstance(previous_files, dict):
        raise ValueError(f"refresh state has invalid files for project: {project.id}")

    refreshed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    records: list[SourceRecord] = []
    new = changed = unchanged = review = 0
    next_files: dict[str, dict[str, object]] = {}

    for root, path in _iter_source_files(project):
        stat = path.stat()
        state_key = str(path)
        previous = previous_files.get(state_key)
        if isinstance(previous, dict) and previous.get("mtime_ns") == stat.st_mtime_ns and previous.get("size") == stat.st_size:
            content_hash = str(previous["content_hash"])
            checked_at = str(previous.get("checked_at", refreshed_at))
            unchanged += 1
        else:
            content_hash = _hash_file(path)
            if not isinstance(previous, dict):
                checked_at = refreshed_at
                new += 1
            elif previous.get("content_hash") != content_hash:
                checked_at = refreshed_at
                changed += 1
            else:
                checked_at = str(previous.get("checked_at", refreshed_at))
                unchanged += 1
        explicit_branch, explicit_note_type, headings = _markdown_context(path)
        classification = classify(
            path,
            rules,
            headings=headings,
            explicit_branch=explicit_branch,
            explicit_note_type=explicit_note_type,
            overrides=overrides,
            override_reference=str(path),
        )
        if classification.is_inbox:
            review += 1
        records.append(_record_from(project, root, path, classification, content_hash, checked_at))
        next_files[state_key] = {
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
            "content_hash": content_hash,
            "checked_at": checked_at,
        }

    records.extend(external_sources)

    project_state["files"] = next_files
    registry_path = _write_registry(vault_root, project, records)
    preliminary_result = RefreshResult(
        scanned=len(records) - len(external_sources),
        external=len(external_sources),
        new=new,
        changed=changed,
        unchanged=unchanged,
        review=review,
        registry_path=registry_path,
        activity_path=vault_root / "Current Work" / "Meaningful Activity.md",
    )
    activity_path = _write_activity(vault_root, project, preliminary_result)
    project_state["refreshed_at"] = refreshed_at
    project_state["last_result"] = {
        "changed": changed,
        "new": new,
        "unchanged": unchanged,
        "review": review,
    }
    _save_state(state_path, state)
    return RefreshResult(
        scanned=preliminary_result.scanned,
        external=preliminary_result.external,
        new=preliminary_result.new,
        changed=preliminary_result.changed,
        unchanged=preliminary_result.unchanged,
        review=preliminary_result.review,
        registry_path=registry_path,
        activity_path=activity_path,
    )


def main(argv: list[str] | None = None) -> int:
    """Run a local-only refresh for the active or selected project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--external-sources", type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--project", help="project ID; defaults to the active project")
    args = parser.parse_args(argv)
    try:
        registry = load_projects(args.projects)
        project = registry.project(args.project) if args.project else registry.active_project
        rules_path = project.rules_file if project.rules_file.is_absolute() else args.projects.parent / project.rules_file
        external_sources_path = args.external_sources or args.projects.parent / "external_sources.toml"
        overrides_path = args.overrides or args.projects.parent / f"{project.id}_vault_overrides.toml"
        rules = load_rules(rules_path)
        result = refresh_project(
            project,
            rules,
            args.vault,
            load_external_sources(external_sources_path, project.id),
            load_overrides(overrides_path, rules),
        )
    except (FileNotFoundError, OSError, json.JSONDecodeError, ProjectRegistryError, RuleValidationError, ValueError) as error:
        print(f"Refresh failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "project": project.id,
                "scanned": result.scanned,
                "external": result.external,
                "new": result.new,
                "changed": result.changed,
                "unchanged": result.unchanged,
                "review": result.review,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
