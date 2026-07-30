import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from services.temperature_event_generator import (
    make_event,
    parse_arguments,
    resolve_profile,
    transform_temperature,
)


class GeneratorScenarioTests(unittest.TestCase):
    def setUp(self):
        self.profile = resolve_profile("pfizer_ultralow")
        self.row = {"temperature_c": -78.5}
        self.event_time = datetime(2026, 7, 29, 12, 0, 0, 123456, tzinfo=timezone.utc)

    def test_normal_stays_inside_profile(self):
        values = [transform_temperature(-78.5, self.profile, "normal", index, 10) for index in range(1, 11)]
        self.assertTrue(all(self.profile.min_c <= value <= self.profile.max_c for value in values))

    def test_recovery_starts_warm_and_ends_at_target(self):
        first = transform_temperature(-78.5, self.profile, "recovery", 1, 5)
        last = transform_temperature(-78.5, self.profile, "recovery", 5, 5)
        self.assertGreater(first, self.profile.max_c)
        self.assertEqual(last, self.profile.target_c)

    def test_mixed_has_normal_failure_and_recovery_phases(self):
        events = [
            make_event("Pod1", self.row, self.profile, "mixed", event_number=index, total_events=9, event_time=self.event_time)
            for index in range(1, 10)
        ]
        phases = [event["scenario_phase"] for event in events]
        self.assertEqual(phases, ["normal", "normal", "normal", "cooling_failure", "cooling_failure", "cooling_failure", "recovery", "recovery", "recovery"])
        self.assertTrue(all(events[index]["event_time"] == events[0]["event_time"] for index in range(len(events))))
        self.assertGreater(events[3]["temperature_c"], self.profile.max_c)
        self.assertEqual(events[-1]["temperature_c"], self.profile.target_c)

    def test_cli_accepts_the_three_current_scenarios_and_summary_controls(self):
        with patch.object(sys, "argv", ["generator", "--scenario", "mixed", "--count", "9", "--seed", "42", "--output-mode", "summary", "--vaccine", "pfizer_ultralow"]):
            args = parse_arguments()
        self.assertEqual(args.scenario, "mixed")
        self.assertEqual(args.count, 9)
        self.assertEqual(args.seed, 42)
        self.assertEqual(args.output_mode, "summary")


if __name__ == "__main__":
    unittest.main()
