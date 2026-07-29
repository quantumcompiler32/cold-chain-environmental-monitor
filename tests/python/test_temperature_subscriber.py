import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app" / "backend"))

from temperature_subscriber import validate_event


class TemperatureSubscriberTests(unittest.TestCase):
    def test_event_requires_profile_and_scenario_provenance(self):
        # A legacy payload without provenance must not enter the database.
        event = {
            "device_id": "vaccine_temperature_simulator",
            "timestamp": "2026-07-21T12:00:00Z",
            "source_timestamp": "2020-12-16T11:26:43",
            "sensor_name": "Pod1",
            "temperature_c": -78.5,
            "status": "STABLE",
        }

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_valid_event_converts_temperature_to_a_number(self):
        # JSON commonly carries numbers as strings; normalize them once.
        event = validate_event(
            {
                "device_id": "vaccine_temperature_simulator",
                "timestamp": "2026-07-21T12:00:00Z",
                "source_timestamp": "2020-12-16T11:26:43",
                "sensor_name": "Pod1",
                "vaccine_type": "pfizer_ultralow",
                "scenario": "normal",
            "temperature_c": "-78.5",
            "status": "STABLE",
            "sensor_tolerance_c": 0.5,
            "temperature_min_possible_c": -79.0,
            "temperature_max_possible_c": -78.0,
            "storage_min_c": -80.0,
            "storage_max_c": -60.0,
            "uncertainty_status": "WITHIN_RANGE",
            "boundary_crossing": False,
            "measurement_confidence": "Approximately +/-0.5 C Type-T thermocouple accuracy",
            }
        )

        self.assertEqual(event["temperature_c"], -78.5)

    def test_rejects_inconsistent_uncertainty_fields(self):
        event = {
            "device_id": "vaccine_temperature_simulator",
            "timestamp": "2026-07-21T12:00:00Z",
            "source_timestamp": "2020-12-16T11:26:43",
            "sensor_name": "Pod1",
            "vaccine_type": "pfizer_ultralow",
            "scenario": "normal",
            "temperature_c": -80.2,
            "status": "TOO_COLD",
            "sensor_tolerance_c": 0.5,
            "temperature_min_possible_c": -80.7,
            "temperature_max_possible_c": -79.7,
            "storage_min_c": -80.0,
            "storage_max_c": -60.0,
            "uncertainty_status": "CLEARLY_TOO_COLD",
            "boundary_crossing": False,
            "measurement_confidence": "Approximately +/-0.5 C Type-T thermocouple accuracy",
        }
        with self.assertRaisesRegex(ValueError, "uncertainty"):
            validate_event(event)


if __name__ == "__main__":
    unittest.main()
