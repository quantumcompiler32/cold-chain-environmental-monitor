import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from vault_rules import RuleValidationError, classify, load_rules, main


class VaultRulesTests(unittest.TestCase):
    def write_rules(self, directory: Path, body: str) -> Path:
        path = directory / "rules.toml"
        path.write_text(body, encoding="utf-8")
        return path

    def test_rejects_a_rule_that_targets_an_unknown_branch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_path = self.write_rules(
                Path(temp_dir),
                """
                version = 1
                inbox_folder = "Inbox"
                branches = ["Current Work"]

                [[rule]]
                name = "bad-target"
                branch = "Does Not Exist"
                note_type = "topic"
                filename_contains = ["sensor"]
                """,
            )

            with self.assertRaisesRegex(RuleValidationError, "Does Not Exist"):
                load_rules(rules_path)

    def test_rejects_rules_with_the_same_matcher_and_different_targets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_path = self.write_rules(
                Path(temp_dir),
                """
                version = 1
                inbox_folder = "Inbox"
                branches = ["System & Sensors", "Analysis & Models"]

                [[rule]]
                name = "sensor-system"
                branch = "System & Sensors"
                note_type = "topic"
                filename_contains = ["sensor"]

                [[rule]]
                name = "sensor-analysis"
                branch = "Analysis & Models"
                note_type = "finding"
                filename_contains = ["sensor"]
                """,
            )

            with self.assertRaisesRegex(RuleValidationError, "conflicts with"):
                load_rules(rules_path)

    def test_explicit_metadata_wins_over_a_matching_rule(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules = load_rules(
                self.write_rules(
                Path(temp_dir),
                """
                version = 1
                inbox_folder = "Inbox"
                branches = ["Current Work", "System & Sensors"]

                    [[rule]]
                    name = "sensor-files"
                    branch = "System & Sensors"
                    note_type = "topic"
                    filename_contains = ["sensor"]
                    """,
                )
            )

            result = classify(
                Path("sensor-reading.md"),
                rules,
                explicit_branch="Current Work",
                explicit_note_type="review",
            )

            self.assertEqual(result.branch, "Current Work")
            self.assertEqual(result.note_type, "review")
            self.assertEqual(result.reason, "explicit metadata")

    def test_uses_a_matching_rule_and_sends_unknown_items_to_inbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules = load_rules(
                self.write_rules(
                Path(temp_dir),
                """
                    version = 1
                    inbox_folder = "Inbox"
                    branches = ["System & Sensors"]

                    [[rule]]
                    name = "sensor-files"
                    branch = "System & Sensors"
                    note_type = "topic"
                    filename_contains = ["sensor"]
                    extensions = [".md"]
                    """,
                )
            )

            matched = classify(Path("sensor-reading.md"), rules)
            unknown = classify(Path("weekly-reflection.txt"), rules)

            self.assertEqual((matched.branch, matched.note_type, matched.reason), (
                "System & Sensors",
                "topic",
                "rule: sensor-files",
            ))
            self.assertEqual((unknown.branch, unknown.note_type, unknown.reason, unknown.is_inbox), (
                None,
                "review",
                "no deterministic rule matched",
                True,
            ))

    def test_invalid_explicit_metadata_goes_to_inbox_with_a_reason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules = load_rules(
                self.write_rules(
                    Path(temp_dir),
                    """
                    version = 1
                    inbox_folder = "Inbox"
                    branches = ["Current Work"]

                    [[rule]]
                    name = "work-files"
                    branch = "Current Work"
                    note_type = "work-item"
                    filename_contains = ["task"]
                    """,
                )
            )

            result = classify(Path("task.md"), rules, explicit_branch="Not a branch")

            self.assertEqual((result.branch, result.note_type, result.is_inbox), (None, "review", True))
            self.assertIn("unknown explicit branch", result.reason)

    def test_check_rules_command_validates_without_scanning_the_vault(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_path = self.write_rules(
                Path(temp_dir),
                """
                version = 1
                inbox_folder = "Inbox"
                branches = ["Current Work"]

                [[rule]]
                name = "work-files"
                branch = "Current Work"
                note_type = "work-item"
                filename_contains = ["task"]
                """,
            )
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(["--check-rules", str(rules_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue(), "Rules valid: 1 branch, 1 rule.\n")

    def test_default_bytesmart_rules_define_every_branch(self):
        rules_path = Path(__file__).with_name("bytesmart_vault_rules.toml")

        rules = load_rules(rules_path)

        self.assertEqual(rules.branches, (
            "Current Work",
            "Connected Sources",
            "System & Sensors",
            "Data Pipeline & Storage",
            "Analysis & Models",
            "Findings & Decisions",
            "Deliverables & Visuals",
        ))
        self.assertEqual((rules.version, rules.inbox_folder), (1, "Inbox"))
        self.assertGreaterEqual(len(rules.rules), 7)


if __name__ == "__main__":
    unittest.main()
