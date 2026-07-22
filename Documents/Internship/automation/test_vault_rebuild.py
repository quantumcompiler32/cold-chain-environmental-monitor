import tempfile
import unittest
from pathlib import Path

from vault_rebuild import apply_plan, build_plan, write_preview


class VaultRebuildTests(unittest.TestCase):
    def make_vault(self, base: Path) -> Path:
        vault = base / "vault"
        registry = vault / "Connected Sources" / "Source Registry.md"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            "| Source ID | Title | Type | Branch | Reference | Authority | Coverage | Sensitivity | Last checked | Hash | Sync | Promotion | Review reason |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| bytesmart-system | System Architecture.md | md | System & Sensors | /live/System Architecture.md | Primary | Unknown | Normal | now | hash | Current | Registry only | — |\n",
            encoding="utf-8",
        )
        artifact = vault / "Artifacts" / "IoT Simulation" / "System Architecture.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("# Architecture\n", encoding="utf-8")
        return vault

    def test_preview_proposes_a_move_without_changing_the_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))

            plan = build_plan(vault, "bytesmart")

            self.assertEqual(len(plan.moves), 1)
            self.assertTrue(plan.moves[0].source.exists())
            self.assertEqual(
                plan.moves[0].destination,
                vault.resolve() / "System & Sensors" / "Reference" / "System Architecture.md",
            )

    def test_apply_moves_only_vault_copies_after_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))
            plan = build_plan(vault, "bytesmart")

            apply_plan(plan, confirm=True)

            self.assertFalse(plan.moves[0].source.exists())
            self.assertTrue(plan.moves[0].destination.exists())

    def test_preview_note_states_that_protected_notes_are_untouched(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))

            preview = write_preview(vault, build_plan(vault, "bytesmart"))

            self.assertIn("Protected notes left untouched", preview.read_text(encoding="utf-8"))

    def test_linked_artifacts_are_held_for_manual_migration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))
            (vault / "Imported Files.md").write_text(
                "[[Artifacts/IoT Simulation/System Architecture.md]]\n", encoding="utf-8"
            )

            plan = build_plan(vault, "bytesmart")

            self.assertEqual(plan.moves, ())
            self.assertEqual(len(plan.linked_candidates), 1)
            self.assertIn("[[Imported Files]]", write_preview(vault, plan).read_text(encoding="utf-8"))

            apply_plan(plan, confirm=True)

            self.assertTrue((vault / "Artifacts" / "IoT Simulation" / "System Architecture.md").exists())

    def test_duplicate_titles_are_not_auto_classified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))
            registry = vault / "Connected Sources" / "Source Registry.md"
            with registry.open("a", encoding="utf-8") as handle:
                handle.write(
                    "| bytesmart-analysis | System Architecture.md | md | Analysis & Models | /live/other.md | Primary | Unknown | Normal | now | hash | Current | Registry only | — |\n"
                )

            self.assertEqual(build_plan(vault, "bytesmart").moves, ())

    def test_preview_preserves_human_content_on_refresh(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))
            plan = build_plan(vault, "bytesmart")
            preview = write_preview(vault, plan)
            preview.write_text(preview.read_text(encoding="utf-8") + "\nMy decision stays.\n", encoding="utf-8")

            write_preview(vault, plan)

            self.assertIn("My decision stays.", preview.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
