import tempfile
import unittest
from pathlib import Path

from vault_dashboard import build_dashboard, write_dashboard


class VaultDashboardTests(unittest.TestCase):
    def make_vault(self, base: Path) -> Path:
        vault = base / "vault"
        registry = vault / "Connected Sources" / "Source Registry.md"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            "| Source ID | Title | Type | Branch | Reference | Authority | Coverage | Sensitivity | Last checked | Hash | Sync | Promotion | Review reason |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| bytesmart-one | One.md | md | Current Work | /live/One.md | Primary | Unknown | Normal | 2026-07-21 12:00 UTC | hash | Current | Registry only | — |\n"
            "| bytesmart-two | Two.md | md | Inbox | /live/Two.md | Primary | Unknown | Normal | 2026-07-21 11:00 UTC | hash | Needs review | Review | unclear |\n"
            "| bytesmart-external-drive | Drive | drive | Connected Sources | drive://x | Primary | Full | Sensitive | 2026-07-20 | metadata-only | Metadata only | Registry only | — |\n",
            encoding="utf-8",
        )
        queue = vault / "Findings & Decisions" / "Review Queue.md"
        queue.parent.mkdir(parents=True)
        queue.write_text("# Review Queue\n", encoding="utf-8")
        decision = vault / "Findings & Decisions" / "Confirm Schema.md"
        decision.write_text(
            "---\n"
            "type: decision\n"
            "project: ByteSmart\n"
            "status: Pending\n"
            "---\n",
            encoding="utf-8",
        )
        state = vault / ".connected-vault" / "refresh-state.json"
        state.parent.mkdir()
        state.write_text(
            '{"version": 1, "projects": {"bytesmart": {"refreshed_at": "2026-07-21 12:30 UTC", "last_result": {"changed": 2, "unchanged": 9}}}}',
            encoding="utf-8",
        )
        work_queue = vault / "Current Internship Work Queue.md"
        work_queue.write_text("## Active\n\n- Check sensors\n\n## Next\n\n- Build model\n\n## Waiting\n\n- Vendor reply\n\n## Blocked\n\n- No blocker\n", encoding="utf-8")
        activity = vault / "Current Work" / "Meaningful Activity.md"
        activity.parent.mkdir(parents=True)
        activity.write_text("## 2026-07-21 12:30 UTC\n\n- Updated source registry.\n", encoding="utf-8")
        return vault

    def test_dashboard_summarizes_local_external_and_review_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))

            health = build_dashboard(vault, "bytesmart")

            self.assertEqual(health.local_sources, 2)
            self.assertEqual(health.external_sources, 1)
            self.assertEqual(health.source_review, 1)
            self.assertEqual(health.decision_review, 1)
            self.assertEqual(health.last_refresh, "2026-07-21 12:30 UTC")
            self.assertEqual(health.changed, 2)
            self.assertEqual(health.unchanged, 9)
            self.assertEqual(health.active_work, 1)
            self.assertEqual(health.next_work, 1)
            self.assertEqual(health.waiting_work, 1)
            self.assertEqual(health.blocked_work, 1)
            self.assertEqual(health.recent_activity, "Updated source registry.")

    def test_dashboard_refresh_preserves_human_notes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = self.make_vault(Path(temp_dir))
            command_center = vault / "ByteSmart Command Center.md"
            command_center.write_text("# ByteSmart Command Center\n\n## Human Notes\n\nKeep this.\n", encoding="utf-8")

            write_dashboard(vault, build_dashboard(vault, "bytesmart"))
            write_dashboard(vault, build_dashboard(vault, "bytesmart"))

            content = command_center.read_text(encoding="utf-8")
            self.assertIn("Keep this.", content)
            self.assertIn("Local sources | 2", content)
            self.assertIn("Source review | 1", content)


if __name__ == "__main__":
    unittest.main()
