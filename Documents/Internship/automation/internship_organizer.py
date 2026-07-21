#!/usr/bin/env python3
"""Safely copy internship artifacts into the Obsidian vault and maintain indexes."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SOURCE = Path("/Users/mokshjoshi/Documents/EverythingLife/Internship")
DEFAULT_VAULT = Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault")
ARTIFACT_ROOT = "Artifacts"

IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "site-packages",
    ".dist-info",
    ".egg-info",
}
IGNORED_FILE_NAMES = {".DS_Store", ".env", ".gitkeep"}
IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".o",
    ".a",
}
IGNORED_NAME_PARTS = {".dist-info", ".egg-info", ".cache"}

CATEGORY_ORDER = (
    "ByteSmart",
    "IoT Simulation",
    "Reports",
    "Data and Research",
    "Code and Automation",
    "Notes and Learning",
    "Reference Material",
    "Inbox",
)


@dataclass(frozen=True)
class OrganizedFile:
    source: Path
    destination: Path
    category: str
    status: str


def is_ignored(path: Path, source_root: Path) -> bool:
    """Return whether a source path is unsafe, generated, or not useful in Obsidian."""
    try:
        relative_parts = path.relative_to(source_root).parts
    except ValueError:
        relative_parts = path.parts

    if any(part in IGNORED_DIR_NAMES for part in relative_parts[:-1]):
        return True
    name = path.name
    if name in IGNORED_FILE_NAMES:
        return True
    if name.lower().endswith(tuple(IGNORED_SUFFIXES)):
        return True
    lowered = name.lower()
    return any(part in lowered for part in IGNORED_NAME_PARTS)


def classify_path(path: Path, source_root: Path) -> str:
    """Classify a file by project meaning, with specific project rules first."""
    relative = path.relative_to(source_root).as_posix().lower()
    name = path.name.lower()
    suffix = path.suffix.lower()

    if any(token in relative for token in ("bytesmart", "byte_smart")):
        return "ByteSmart"
    if suffix in {".csv", ".json", ".ipynb", ".pkl", ".npy", ".npz"} or any(
        token in name for token in ("dataset", "data", "telemetry")
    ):
        return "Data and Research"
    if any(token in relative for token in ("iot_simulation", "mosquitto", "mqtt")):
        return "IoT Simulation"
    if any(token in name for token in ("publisher", "subscriber", "mosquitto", "database", "pipeline", "startup", "shutdown", "iot")):
        return "IoT Simulation"
    if any(token in name for token in ("report", "professionalism", "introduction", "demo")):
        return "Reports"
    if suffix in {".py", ".sh", ".zsh", ".command", ".conf", ".ini", ".toml", ".sql", ".js", ".ts"}:
        return "Code and Automation"
    if suffix == ".md" and any(token in name for token in ("cheat", "learn", "library", "notes")):
        return "Notes and Learning"
    if suffix in {".pdf", ".docx", ".pptx", ".html", ".txt"}:
        return "Reference Material"
    return "Inbox"


def _safe_destination(destination: Path) -> Path:
    """Preserve the source filename while avoiding overwrites in the vault."""
    version = 1
    candidate = destination
    while candidate.exists():
        candidate = destination.with_name(f"{destination.stem} ({version}){destination.suffix}")
        version += 1
    return candidate


def iter_source_files(source_root: Path) -> Iterable[Path]:
    for path in sorted(source_root.rglob("*")):
        if path.is_file() and not is_ignored(path, source_root):
            yield path


def copy_file(source: Path, vault_root: Path, source_root: Path) -> OrganizedFile:
    category = classify_path(source, source_root)
    destination_dir = vault_root / ARTIFACT_ROOT / category
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name

    if destination.exists():
        if source.stat().st_size == destination.stat().st_size and source.read_bytes() == destination.read_bytes():
            return OrganizedFile(source, destination, category, "unchanged")
        destination = _safe_destination(destination)

    shutil.copy2(source, destination)
    return OrganizedFile(source, destination, category, "copied")


def _link_for_note(path: Path, vault_root: Path) -> str:
    relative_path = path.relative_to(vault_root)
    relative = relative_path.with_suffix("").as_posix() if relative_path.suffix == ".md" else relative_path.as_posix()
    return f"[[{relative}]]"


def write_indexes(vault_root: Path, source_root: Path, records: list[OrganizedFile]) -> None:
    grouped: dict[str, list[OrganizedFile]] = {category: [] for category in CATEGORY_ORDER}
    for record in records:
        grouped.setdefault(record.category, []).append(record)

    manifest_lines = [
        "---",
        "tags: [internship, imported-artifact, automated-index]",
        "---",
        "# Imported Internship Files",
        "",
        "This manifest is regenerated by `automation/internship_organizer.py`. Original source files remain in place; vault copies are organized by category.",
        "",
    ]
    for category in CATEGORY_ORDER:
        entries = grouped.get(category, [])
        manifest_lines.extend([f"## {category}", ""])
        if not entries:
            manifest_lines.append("_No files yet._")
        else:
            for record in sorted(entries, key=lambda item: item.destination.name.lower()):
                source_relative = record.source
                try:
                    source_relative = record.source.relative_to(source_root)
                except ValueError:
                    pass
                link = _link_for_note(record.destination, vault_root)
                manifest_lines.append(f"- {link} — `{source_relative}` ({record.status})")
        manifest_lines.append("")

    (vault_root / "Imported Internship Files.md").write_text("\n".join(manifest_lines), encoding="utf-8")

    category_lines = [
        "---",
        "tags: [internship, index, navigation]",
        "---",
        "# Category Index",
        "",
        "Use this as the fast navigation map for imported project files.",
        "",
    ]
    for category in CATEGORY_ORDER:
        category_lines.append(f"- [[Imported Internship Files#{category}|{category}]]")
    (vault_root / "Category Index.md").write_text("\n".join(category_lines) + "\n", encoding="utf-8")


def organize_once(source_root: Path = DEFAULT_SOURCE, vault_root: Path = DEFAULT_VAULT) -> list[OrganizedFile]:
    source_root = source_root.expanduser().resolve()
    vault_root = vault_root.expanduser().resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")
    vault_root.mkdir(parents=True, exist_ok=True)
    records = [copy_file(path, vault_root, source_root) for path in iter_source_files(source_root)]
    write_indexes(vault_root, source_root, records)
    return records


def _snapshot(source_root: Path) -> dict[str, tuple[int, int]]:
    return {str(path): (path.stat().st_mtime_ns, path.stat().st_size) for path in iter_source_files(source_root)}


def watch(source_root: Path, vault_root: Path, interval: float) -> None:
    previous = None
    while True:
        current = _snapshot(source_root)
        if current != previous:
            records = organize_once(source_root, vault_root)
            print(json.dumps({"processed": len(records)}), flush=True)
            previous = current
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--watch", action="store_true", help="watch the source recursively")
    parser.add_argument("--interval", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        if args.watch:
            watch(args.source.expanduser().resolve(), args.vault.expanduser().resolve(), args.interval)
        else:
            records = organize_once(args.source, args.vault)
            counts: dict[str, int] = {}
            for record in records:
                counts[record.status] = counts.get(record.status, 0) + 1
            print(json.dumps({"files": len(records), "statuses": counts}, indent=2))
        return 0
    except (FileNotFoundError, OSError) as error:
        print(f"internship-organizer: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
