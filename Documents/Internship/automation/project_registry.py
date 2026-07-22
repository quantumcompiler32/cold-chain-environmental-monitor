"""Load the local project registry used by the ByteSmart vault refresh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


REGISTRY_VERSION = 1


class ProjectRegistryError(ValueError):
    """Raised when the project registry cannot select a safe refresh target."""


@dataclass(frozen=True)
class Project:
    id: str
    title: str
    source_roots: tuple[Path, ...]
    rules_file: Path
    active: bool
    dashboard_note: str = ""
    work_queue_note: str = ""


@dataclass(frozen=True)
class ProjectRegistry:
    projects: tuple[Project, ...]

    @property
    def active_project(self) -> Project:
        return next(project for project in self.projects if project.active)

    def project(self, project_id: str) -> Project:
        for project in self.projects:
            if project.id == project_id:
                return project
        raise ProjectRegistryError(f"unknown project: {project_id}")


def _required_string(value: object, field: str, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectRegistryError(f"{location}.{field} must be a non-empty string")
    return value.strip()


def _source_roots(value: object, location: str) -> tuple[Path, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ProjectRegistryError(f"{location}.source_roots must be a non-empty list of paths")
    return tuple(Path(item) for item in value)


def _load_project(raw: object, position: int) -> Project:
    location = f"project[{position}]"
    if not isinstance(raw, dict):
        raise ProjectRegistryError(f"{location} must be a table")
    active = raw.get("active")
    if not isinstance(active, bool):
        raise ProjectRegistryError(f"{location}.active must be true or false")
    return Project(
        id=_required_string(raw.get("id"), "id", location),
        title=_required_string(raw.get("title"), "title", location),
        source_roots=_source_roots(raw.get("source_roots"), location),
        rules_file=Path(_required_string(raw.get("rules_file"), "rules_file", location)),
        active=active,
        dashboard_note=str(raw.get("dashboard_note", "")).strip(),
        work_queue_note=str(raw.get("work_queue_note", "")).strip(),
    )


def _note_name(value: str, fallback: str, location: str) -> str:
    name = value or fallback
    path = Path(name)
    if path.name != name or name in {".", ".."}:
        raise ProjectRegistryError(f"{location} note name must be a single vault filename")
    return name


def load_projects(path: Path) -> ProjectRegistry:
    """Load the registry without scanning any project source files."""
    with path.open("rb") as registry_file:
        raw = tomllib.load(registry_file)
    version = raw.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version != REGISTRY_VERSION:
        raise ProjectRegistryError(f"root.version must be {REGISTRY_VERSION}")
    raw_projects = raw.get("project")
    if not isinstance(raw_projects, list) or not raw_projects:
        raise ProjectRegistryError("root.project must contain at least one project")
    projects = tuple(_load_project(raw_project, position) for position, raw_project in enumerate(raw_projects, start=1))
    ids = [project.id for project in projects]
    if len(set(ids)) != len(ids):
        raise ProjectRegistryError("project IDs must be unique")
    if any(other.startswith(f"{project_id}-") for project_id in ids for other in ids if other != project_id):
        raise ProjectRegistryError("project IDs cannot overlap by hyphenated prefix")
    if sum(project.active for project in projects) != 1:
        raise ProjectRegistryError("the registry must have exactly one active project")
    normalized = tuple(
        Project(
            id=project.id,
            title=project.title,
            source_roots=project.source_roots,
            rules_file=project.rules_file,
            active=project.active,
            dashboard_note=_note_name(project.dashboard_note, f"{project.title} Command Center", f"project {project.id}"),
            work_queue_note=_note_name(project.work_queue_note, f"{project.title} Work Queue", f"project {project.id}"),
        )
        for project in projects
    )
    if len({project.dashboard_note for project in normalized}) != len(normalized):
        raise ProjectRegistryError("project dashboard_note values must be unique")
    if len({project.work_queue_note for project in normalized}) != len(normalized):
        raise ProjectRegistryError("project work_queue_note values must be unique")
    return ProjectRegistry(projects=normalized)
