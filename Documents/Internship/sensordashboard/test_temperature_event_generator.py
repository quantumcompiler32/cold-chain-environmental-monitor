import unittest
from datetime import datetime

from temperature_event_generator import (
    VaccineProfile,
    adapt_source_temperature,
    classify_temperature,
    make_event,
    resolve_profile,
    transform_temperature,
)


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


if __name__ == "__main__":
    unittest.main()
