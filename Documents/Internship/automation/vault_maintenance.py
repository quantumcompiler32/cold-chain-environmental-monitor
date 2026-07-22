"""Run the token-free ByteSmart refresh and review workflow in one command."""

from __future__ import annotations

import argparse
from pathlib import Path

from project_registry import load_projects
from vault_refresh import main as refresh_main
from vault_review import main as review_main
from vault_dashboard import main as dashboard_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", type=Path, default=Path("automation/projects.toml"))
    parser.add_argument("--vault", type=Path, default=Path("/Users/mokshjoshi/Documents/Internship/Obsidian Vault"))
    parser.add_argument("--project", help="refresh one registered project instead of every project")
    args = parser.parse_args(argv)
    registry = load_projects(args.projects)
    projects = (registry.project(args.project),) if args.project else registry.projects
    for project in projects:
        common = ["--projects", str(args.projects), "--vault", str(args.vault), "--project", project.id]
        if refresh_main(common) != 0 or review_main(common) != 0 or dashboard_main(common) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
