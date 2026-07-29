import unittest
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app" / "backend"))

from temperature_event_generator import (
    VaccineProfile,
    adapt_source_temperature,
    classify_temperature,
    make_event,
    resolve_profile,
    transform_temperature,
)
from temperature_uncertainty import SENSOR_TOLERANCE_C, classify_uncertainty, possible_temperature_range


class TemperatureEventGeneratorTests(unittest.TestCase):
    def setUp(self):
        # Every test starts with the same resolved Pfizer profile and source
        # row so scenario assertions remain deterministic.
        self.pfizer = resolve_profile("pfizer_ultralow")
        self.source_row = {
            "source_timestamp": datetime(2020, 12, 16, 11, 26, 43),
            "temperature_c": -78.5,
        }

    def test_event_contains_profile_scenario_and_original_source_timestamp(self):
        # The event must preserve provenance while adding generated metadata.
        event = make_event(
            "Pod1",
            self.source_row,
            self.pfizer,
            "normal",
            event_number=1,
            total_events=5,
        )

        self.assertEqual(event["vaccine_type"], "pfizer_ultralow")
        self.assertEqual(event["scenario"], "normal")
        self.assertEqual(event["source_timestamp"], "2020-12-16T11:26:43")
        self.assertEqual(event["temperature_c"], -78.5)
        self.assertEqual(event["status"], "STABLE")
        self.assertEqual(event["sensor_tolerance_c"], SENSOR_TOLERANCE_C)
        self.assertEqual(event["temperature_min_possible_c"], -79.0)
        self.assertEqual(event["temperature_max_possible_c"], -78.0)
        self.assertEqual(event["uncertainty_status"], "WITHIN_RANGE")

    def test_pfizer_status_uses_the_paper_boundaries(self):
        # Test both inclusive boundaries and readings just outside them.
        self.assertEqual(classify_temperature(-78.5, self.pfizer), "STABLE")
        self.assertEqual(classify_temperature(-80.0, self.pfizer), "ACCEPTABLE")
        self.assertEqual(classify_temperature(-80.01, self.pfizer), "TOO_COLD")
        self.assertEqual(classify_temperature(-60.0, self.pfizer), "ACCEPTABLE")
        self.assertEqual(classify_temperature(-59.99, self.pfizer), "TOO_WARM")

    def test_outliers_alternate_between_cold_and_warm_every_twentieth_event(self):
        # The bounded runner's 20-event default intentionally produces one
        # visible outlier per Pod.
        cold = transform_temperature(-78.5, self.pfizer, "outlier", 20, 40)
        warm = transform_temperature(-78.5, self.pfizer, "outlier", 40, 40)

        self.assertEqual(cold, -81.0)
        self.assertEqual(warm, -59.0)

    def test_failure_is_sustained_and_recovery_returns_to_target(self):
        # Failure stays outside the range; recovery ends at the target.
        failure = transform_temperature(-78.5, self.pfizer, "failure", 1, 3)
        recovery_start = transform_temperature(-78.5, self.pfizer, "recovery", 1, 3)
        recovery_end = transform_temperature(-78.5, self.pfizer, "recovery", 3, 3)

        self.assertEqual(failure, -55.0)
        self.assertEqual(recovery_start, -55.0)
        self.assertEqual(recovery_end, -78.5)

    def test_moderna_requires_explicit_bounds(self):
        # Moderna's bounds are supplied by the operator, not silently guessed
        # by the Python command-line interface.
        with self.assertRaisesRegex(ValueError, "both --min-temp and --max-temp"):
            resolve_profile("moderna")

        moderna = resolve_profile("moderna", min_temp=-35, max_temp=-25)
        self.assertIsInstance(moderna, VaccineProfile)
        self.assertEqual(moderna.target_c, -32.5)

    def test_normal_moderna_events_keep_source_variation_near_moderna_target(self):
        moderna = resolve_profile("moderna", min_temp=-50, max_temp=-15)
        # The source CSV is a Pfizer experiment, so the generator translates
        # its deviation rather than replaying roughly -80°C as Moderna data.
        self.assertAlmostEqual(adapt_source_temperature(-77.5, moderna), -31.5)

    def test_normal_stays_inside_the_selected_profile_safe_range(self):
        # Normal is the safe baseline for the dashboard. Source excursions are
        # bounded to the operator-selected profile instead of creating an
        # incident accidentally.
        self.assertEqual(
            transform_temperature(-90.0, self.pfizer, "normal", 1, 3),
            -80.0,
        )
        self.assertEqual(
            transform_temperature(-20.0, self.pfizer, "normal", 2, 3),
            -60.0,
        )

        moderna = resolve_profile("moderna", min_temp=-50, max_temp=-15)
        self.assertEqual(
            transform_temperature(-110.0, moderna, "normal", 1, 3),
            -50.0,
        )
        self.assertEqual(
            transform_temperature(-20.0, moderna, "normal", 2, 3),
            -15.0,
        )

    def test_uncertainty_examples_match_the_documented_policy(self):
        self.assertEqual(possible_temperature_range(-80.2), (-80.7, -79.7))
        self.assertEqual(classify_uncertainty(-80.2, -80, -60)["uncertainty_status"], "BORDERLINE_COLD")
        self.assertTrue(classify_uncertainty(-80.2, -80, -60)["boundary_crossing"])
        self.assertEqual(classify_uncertainty(-79.8, -80, -60)["uncertainty_status"], "BORDERLINE_COLD")
        self.assertEqual(classify_uncertainty(-81.0, -80, -60)["uncertainty_status"], "CLEARLY_TOO_COLD")

    def test_non_outlier_events_keep_the_selected_profile_baseline(self):
        moderna = resolve_profile("moderna", min_temp=-50, max_temp=-15)
        value = transform_temperature(-78.5, moderna, "outlier", 1, 20)
        self.assertAlmostEqual(value, -32.5)


if __name__ == "__main__":
    unittest.main()
