"""Verify the deterministic E2E manifest and generated report contract."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EndToEndAssetTests(unittest.TestCase):
    def test_manifest_covers_all_public_deterministic_scenarios(self):
        manifest = json.loads((ROOT / "tests" / "e2e_scenarios.json").read_text())
        cases = manifest["cases"]

        self.assertEqual(manifest["version"], 1)
        self.assertEqual(
            [case["scenario"] for case in cases],
            ["normal", "warning", "recovery", "mixed", "outlier"],
        )
        self.assertEqual(len({case["name"] for case in cases}), len(cases))
        for case in cases:
            self.assertGreater(case["count"], 0)
            self.assertIsInstance(case["seed"], int)
            self.assertIn("required_statuses", case)
            self.assertIn("required_operational_statuses", case)


if __name__ == "__main__":
    unittest.main()
