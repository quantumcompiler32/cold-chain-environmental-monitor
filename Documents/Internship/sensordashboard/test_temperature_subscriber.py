import unittest

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

        with self.assertRaisesRegex(ValueError, "scenario, vaccine_type"):
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
            }
        )

        self.assertEqual(event["temperature_c"], -78.5)


if __name__ == "__main__":
    unittest.main()
