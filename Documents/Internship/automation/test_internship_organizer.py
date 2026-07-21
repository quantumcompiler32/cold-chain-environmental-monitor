import tempfile
import unittest
from pathlib import Path

from internship_organizer import classify_path, is_ignored, organize_once


class InternshipOrganizerTests(unittest.TestCase):
    def test_ignores_secrets_generated_files_and_virtual_environment(self):
        root = Path("/tmp/internship")
        self.assertTrue(is_ignored(root / ".env", root))
        self.assertTrue(is_ignored(root / ".DS_Store", root))
        self.assertTrue(is_ignored(root / ".gitkeep", root))
        self.assertTrue(is_ignored(root / ".venv/bin/python", root))
        self.assertTrue(is_ignored(root / "__pycache__/module.pyc", root))
        self.assertTrue(is_ignored(root / "config.env.example", root) is False)

    def test_classifies_project_files_by_meaning(self):
        root = Path("/tmp/internship")
        self.assertEqual(classify_path(root / "byteSmart_visual_workflow_diagram.md", root), "ByteSmart")
        self.assertEqual(classify_path(root / "IoT_Simulation_Obsidian_Final_Updated/README.md", root), "IoT Simulation")
        self.assertEqual(classify_path(root / "Professionalism 6.17.2026.md", root), "Reports")
        self.assertEqual(classify_path(root / "telemetry.csv", root), "Data and Research")
        self.assertEqual(classify_path(root / "IoT_Simulation_Obsidian_Final_Updated/exports/telemetry.csv", root), "Data and Research")
        self.assertEqual(classify_path(root / "install_iot_shortcuts.sh", root), "IoT Simulation")

    def test_copies_files_without_overwriting_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "source"
            vault = base / "vault"
            source.mkdir()
            (source / "byteSmart_notes.md").write_text("first", encoding="utf-8")
            (source / ".env").write_text("SECRET=do-not-copy", encoding="utf-8")
            (source / ".venv").mkdir()
            (source / ".venv" / "python").write_text("generated", encoding="utf-8")

            first = organize_once(source, vault)
            self.assertEqual(len(first), 1)
            destination = vault / "Artifacts" / "ByteSmart" / "byteSmart_notes.md"
            self.assertTrue(destination.exists())
            self.assertFalse((vault / "Artifacts" / "ByteSmart" / ".env").exists())
            self.assertTrue((vault / "Imported Internship Files.md").exists())

            (source / "byteSmart_notes.md").write_text("updated", encoding="utf-8")
            second = organize_once(source, vault)
            destinations = [record.destination for record in second]
            self.assertEqual(len(destinations), 1)
            self.assertNotEqual(destinations[0], destination)
            self.assertEqual(destination.read_text(encoding="utf-8"), "first")

            (source / "byteSmart_notes.md").write_text("third", encoding="utf-8")
            third = organize_once(source, vault)
            self.assertNotEqual(third[0].destination, second[0].destination)
            self.assertEqual(second[0].destination.read_text(encoding="utf-8"), "updated")


if __name__ == "__main__":
    unittest.main()
