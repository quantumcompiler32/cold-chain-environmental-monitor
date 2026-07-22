import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path

from project_registry import Project
from vault_refresh import load_external_sources, main, refresh_project
from vault_rules import load_overrides, load_rules


class VaultRefreshTests(unittest.TestCase):
    def write_rules(self, directory: Path) -> Path:
        rules_path = directory / "rules.toml"
        rules_path.write_text(
            """
            version = 1
            inbox_folder = "Inbox"
            branches = ["System & Sensors"]

            [[rule]]
            name = "sensor-files"
            branch = "System & Sensors"
            note_type = "topic"
            filename_contains = ["sensor"]
            """,
            encoding="utf-8",
        )
        return rules_path

    def test_refresh_indexes_sources_without_copying_originals_and_logs_initial_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_root = base / "source"
            vault_root = base / "vault"
            source_root.mkdir()
            (source_root / "sensor-guide.md").write_text("# Sensor guide\n", encoding="utf-8")
            (source_root / "reflection.txt").write_text("keep this original", encoding="utf-8")
            rules_path = self.write_rules(base)
            project = Project(
                id="bytesmart",
                title="ByteSmart",
                source_roots=(source_root,),
                rules_file=rules_path,
                active=True,
            )

            result = refresh_project(project, load_rules(rules_path), vault_root)

            self.assertEqual((result.scanned, result.new, result.changed, result.unchanged, result.review), (2, 2, 0, 0, 1))
            self.assertEqual((source_root / "reflection.txt").read_text(encoding="utf-8"), "keep this original")
            registry = (vault_root / "Connected Sources" / "Source Registry.md").read_text(encoding="utf-8")
            self.assertIn("System & Sensors", registry)
            self.assertIn("Inbox", registry)
            self.assertIn("reflection.txt", registry)
            self.assertIn("no deterministic rule matched", registry)
            activity = (vault_root / "Current Work" / "Meaningful Activity.md").read_text(encoding="utf-8")
            self.assertIn("2 new", activity)
            self.assertIn("1 needs review", activity)

    def test_refresh_skips_unchanged_sources_and_logs_a_material_source_change_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_root = base / "source"
            vault_root = base / "vault"
            source_root.mkdir()
            sensor = source_root / "sensor-guide.md"
            sensor.write_text("first", encoding="utf-8")
            rules_path = self.write_rules(base)
            project = Project(
                id="bytesmart",
                title="ByteSmart",
                source_roots=(source_root,),
                rules_file=rules_path,
                active=True,
            )
            rules = load_rules(rules_path)

            refresh_project(project, rules, vault_root)
            unchanged = refresh_project(project, rules, vault_root)
            sensor.write_text("second", encoding="utf-8")
            changed = refresh_project(project, rules, vault_root)

            self.assertEqual((unchanged.new, unchanged.changed, unchanged.unchanged), (0, 0, 1))
            self.assertEqual((changed.new, changed.changed, changed.unchanged), (0, 1, 0))
            activity = (vault_root / "Current Work" / "Meaningful Activity.md").read_text(encoding="utf-8")
            self.assertEqual(activity.count("Indexed 1 source"), 2)

    def test_refresh_keeps_the_registry_stable_when_nothing_changed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_root = base / "source"
            vault_root = base / "vault"
            source_root.mkdir()
            (source_root / "sensor-guide.md").write_text("first", encoding="utf-8")
            rules_path = self.write_rules(base)
            project = Project(
                id="bytesmart",
                title="ByteSmart",
                source_roots=(source_root,),
                rules_file=rules_path,
                active=True,
            )
            rules = load_rules(rules_path)

            first = refresh_project(project, rules, vault_root)
            first_registry = first.registry_path.read_text(encoding="utf-8")
            first_modified_at = first.registry_path.stat().st_mtime_ns
            second = refresh_project(project, rules, vault_root)

            self.assertEqual(second.registry_path.read_text(encoding="utf-8"), first_registry)
            self.assertEqual(second.registry_path.stat().st_mtime_ns, first_modified_at)

    def test_source_ids_do_not_collide_between_project_source_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            first_root = base / "first"
            second_root = base / "second"
            vault_root = base / "vault"
            first_root.mkdir()
            second_root.mkdir()
            (first_root / "sensor-guide.md").write_text("first", encoding="utf-8")
            (second_root / "sensor-guide.md").write_text("second", encoding="utf-8")
            rules_path = self.write_rules(base)
            project = Project(
                id="bytesmart",
                title="ByteSmart",
                source_roots=(first_root, second_root),
                rules_file=rules_path,
                active=True,
            )

            result = refresh_project(project, load_rules(rules_path), vault_root)
            source_ids = [
                line.split("|")[1].strip()
                for line in result.registry_path.read_text(encoding="utf-8").splitlines()
                if line.startswith("| bytesmart-")
            ]

            self.assertEqual(len(source_ids), 2)
            self.assertEqual(len(set(source_ids)), 2)

    def test_loads_external_source_records_without_scanning_their_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "external_sources.toml"
            path.write_text(
                """
                version = 1

                [[source]]
                project = "bytesmart"
                id = "daily-reports"
                title = "Gmail daily reports"
                source_type = "gmail"
                branch = "Connected Sources"
                reference = "Gmail search: subject:Daily Report"
                authority = "Primary"
                coverage = "Partial"
                sensitivity = "Sensitive"
                checked_at = "2026-07-21"
                sync_status = "Current"
                promotion_status = "Registry only"
                """,
                encoding="utf-8",
            )

            sources = load_external_sources(path, "bytesmart")

            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].source_id, "bytesmart-external-daily-reports")
            self.assertEqual(sources[0].sensitivity, "Sensitive")

    def test_manual_override_files_an_otherwise_ambiguous_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_root = base / "source"
            vault_root = base / "vault"
            source_root.mkdir()
            (source_root / "System Architecture.md").write_text("# System Architecture\n", encoding="utf-8")
            rules_path = self.write_rules(base)
            overrides_path = base / "overrides.toml"
            overrides_path.write_text(
                """
                version = 1

                [[override]]
                reference = "{source_root / 'System Architecture.md'}"
                branch = "System & Sensors"
                note_type = "topic"
                """.replace("{source_root / 'System Architecture.md'}", str(source_root / "System Architecture.md")),
                encoding="utf-8",
            )
            project = Project(
                id="bytesmart",
                title="ByteSmart",
                source_roots=(source_root,),
                rules_file=rules_path,
                active=True,
            )

            result = refresh_project(project, load_rules(rules_path), vault_root, overrides=load_overrides(overrides_path))

            self.assertEqual(result.review, 0)
            registry = result.registry_path.read_text(encoding="utf-8")
            self.assertIn("| System Architecture.md | md | System & Sensors |", registry)
            self.assertIn("Manual override", registry)

    def test_manual_override_applies_to_only_its_exact_source_reference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            first_root = base / "first"
            second_root = base / "second"
            vault_root = base / "vault"
            first_root.mkdir()
            second_root.mkdir()
            first_readme = first_root / "README.md"
            second_readme = second_root / "README.md"
            first_readme.write_text("first", encoding="utf-8")
            second_readme.write_text("second", encoding="utf-8")
            rules_path = self.write_rules(base)
            overrides_path = base / "overrides.toml"
            overrides_path.write_text(
                f"""
                version = 1

                [[override]]
                reference = "{first_readme}"
                branch = "System & Sensors"
                note_type = "topic"
                """,
                encoding="utf-8",
            )
            project = Project(
                id="bytesmart",
                title="ByteSmart",
                source_roots=(first_root, second_root),
                rules_file=rules_path,
                active=True,
            )

            result = refresh_project(project, load_rules(rules_path), vault_root, overrides=load_overrides(overrides_path))

            self.assertEqual(result.review, 1)
            registry = result.registry_path.read_text(encoding="utf-8")
            self.assertEqual(registry.count("Manual override"), 1)

    def test_refresh_command_can_target_a_registered_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_root = base / "source"
            vault_root = base / "vault"
            source_root.mkdir()
            (source_root / "sensor-guide.md").write_text("sensor", encoding="utf-8")
            self.write_rules(base)
            projects_path = base / "projects.toml"
            projects_path.write_text(
                f"""
                version = 1

                [[project]]
                id = "bytesmart"
                title = "ByteSmart"
                source_roots = ["{source_root}"]
                rules_file = "rules.toml"
                active = true
                """,
                encoding="utf-8",
            )
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(["--projects", str(projects_path), "--vault", str(vault_root), "--project", "bytesmart"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output.getvalue()), {
                "changed": 0,
                "external": 0,
                "new": 1,
                "project": "bytesmart",
                "review": 0,
                "scanned": 1,
                "unchanged": 0,
            })


if __name__ == "__main__":
    unittest.main()
