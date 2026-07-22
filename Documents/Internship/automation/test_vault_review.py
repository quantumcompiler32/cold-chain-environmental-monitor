import tempfile
import unittest
from pathlib import Path

from project_registry import Project
from vault_review import collect_review_items, write_review_queue


class VaultReviewTests(unittest.TestCase):
    def project(self) -> Project:
        return Project(
            id="bytesmart",
            title="ByteSmart",
            source_roots=(),
            rules_file=Path("bytesmart_vault_rules.toml"),
            active=True,
        )

    def write_registry(self, vault_root: Path) -> None:
        registry_path = vault_root / "Connected Sources" / "Source Registry.md"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(
            "| Source ID | Title | Type | Branch | Reference | Authority | Coverage | Sensitivity | Last checked | Hash | Sync | Promotion | Review reason |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| bytesmart-review | unclear.md | md | Inbox | /source/unclear.md | Primary | Unknown | Normal | now | abc | Needs review | Review | no deterministic rule matched |\n"
            "| bytesmart-current | sensor.md | md | System & Sensors | /source/sensor.md | Primary | Unknown | Normal | now | def | Current | Registry only | — |\n",
            encoding="utf-8",
        )

    def test_collects_source_and_pending_decision_review_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            self.write_registry(vault_root)
            decision = vault_root / "Findings & Decisions" / "Choose database.md"
            decision.parent.mkdir(parents=True)
            decision.write_text(
                "---\n"
                "type: decision\n"
                "status: Pending\n"
                "project: ByteSmart\n"
                "---\n\n"
                "# Choose database\n",
                encoding="utf-8",
            )

            items = collect_review_items(vault_root, self.project())

            self.assertEqual(len(items.source_items), 1)
            self.assertEqual(items.source_items[0].reason, "no deterministic rule matched")
            self.assertEqual(len(items.decision_items), 1)
            self.assertEqual(items.decision_items[0].title, "Choose database")

    def test_writes_one_readable_queue_without_creating_notes_for_each_item(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            self.write_registry(vault_root)

            queue_path = write_review_queue(vault_root, self.project(), collect_review_items(vault_root, self.project()))

            self.assertEqual(queue_path, vault_root / "Findings & Decisions" / "Review Queue.md")
            self.assertTrue(queue_path.exists())
            self.assertIn("unclear.md", queue_path.read_text(encoding="utf-8"))
            self.assertEqual(len(list((vault_root / "Findings & Decisions").glob("*.md"))), 1)

    def test_preserves_human_notes_outside_the_managed_project_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            self.write_registry(vault_root)
            queue_path = vault_root / "Findings & Decisions" / "Review Queue.md"
            queue_path.parent.mkdir(parents=True)
            queue_path.write_text("# Existing Queue\n\n## Human Notes\n\nKeep this.\n", encoding="utf-8")

            write_review_queue(vault_root, self.project(), collect_review_items(vault_root, self.project()))

            content = queue_path.read_text(encoding="utf-8")
            self.assertIn("Keep this.", content)
            self.assertIn("managed:review-queue:bytesmart:start", content)

    def test_preserves_a_protected_heading_inside_the_managed_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_root = Path(temp_dir)
            self.write_registry(vault_root)
            queue_path = vault_root / "Findings & Decisions" / "Review Queue.md"
            queue_path.parent.mkdir(parents=True)
            queue_path.write_text(
                "<!-- managed:review-queue:bytesmart:start -->\n"
                "# Review Queue — ByteSmart\n\n"
                "## Human Notes\n\n"
                "Keep this protected note.\n"
                "<!-- managed:review-queue:bytesmart:end -->\n",
                encoding="utf-8",
            )

            write_review_queue(vault_root, self.project(), collect_review_items(vault_root, self.project()))

            self.assertIn("Keep this protected note.", queue_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
