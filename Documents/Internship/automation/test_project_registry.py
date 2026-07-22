import tempfile
import unittest
from pathlib import Path

from project_registry import ProjectRegistryError, load_projects


class ProjectRegistryTests(unittest.TestCase):
    def write_registry(self, directory: Path, body: str) -> Path:
        path = directory / "projects.toml"
        path.write_text(body, encoding="utf-8")
        return path

    def test_loads_the_active_project_with_its_own_source_roots_and_rules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = load_projects(
                self.write_registry(
                    Path(temp_dir),
                    """
                    version = 1

                    [[project]]
                    id = "bytesmart"
                    title = "ByteSmart"
                    source_roots = ["/projects/bytesmart"]
                    rules_file = "bytesmart_vault_rules.toml"
                    active = true
                    """,
                )
            )

            project = registry.active_project

            self.assertEqual(project.id, "bytesmart")
            self.assertEqual(project.title, "ByteSmart")
            self.assertEqual(project.source_roots, (Path("/projects/bytesmart"),))
            self.assertEqual(project.rules_file, Path("bytesmart_vault_rules.toml"))

    def test_rejects_multiple_active_projects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_registry(
                Path(temp_dir),
                """
                version = 1

                [[project]]
                id = "bytesmart"
                title = "ByteSmart"
                source_roots = ["/projects/bytesmart"]
                rules_file = "bytesmart_vault_rules.toml"
                active = true

                [[project]]
                id = "next-project"
                title = "Next Project"
                source_roots = ["/projects/next"]
                rules_file = "next_project_rules.toml"
                active = true
                """,
            )

            with self.assertRaisesRegex(ProjectRegistryError, "exactly one active"):
                load_projects(path)

    def test_finds_a_non_active_project_by_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = load_projects(
                self.write_registry(
                    Path(temp_dir),
                    """
                    version = 1

                    [[project]]
                    id = "bytesmart"
                    title = "ByteSmart"
                    source_roots = ["/projects/bytesmart"]
                    rules_file = "bytesmart_vault_rules.toml"
                    active = true

                    [[project]]
                    id = "next-project"
                    title = "Next Project"
                    source_roots = ["/projects/next"]
                    rules_file = "next_project_rules.toml"
                    active = false
                    """,
                )
            )

            self.assertEqual(registry.project("next-project").title, "Next Project")

    def test_default_registry_starts_with_bytesmart(self):
        registry = load_projects(Path(__file__).with_name("projects.toml"))

        self.assertEqual(registry.active_project.id, "bytesmart")
        self.assertEqual(registry.active_project.title, "ByteSmart")


if __name__ == "__main__":
    unittest.main()
