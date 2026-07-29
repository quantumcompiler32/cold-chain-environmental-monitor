import unittest
from datetime import datetime, timezone
from uuid import UUID

from services.temperature_event_generator import make_event, resolve_profile
from services.temperature_subscriber import validate_event


class EventContractTests(unittest.TestCase):
    def test_generated_event_uses_current_utc_time_and_preserves_source_time(self):
        event = make_event(
            "Pod1",
            {
                "source_timestamp": datetime(2020, 12, 16, 11, 26, 43),
                "temperature_c": -78.5,
            },
            resolve_profile("pfizer_ultralow"),
            "normal",
            event_number=1,
            total_events=1,
            event_id="2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
            event_time=datetime(2026, 7, 29, 12, 0, 0, 123456, tzinfo=timezone.utc),
        )
        event_time = datetime.fromisoformat(event["event_time"])
        source_time = datetime.fromisoformat(event["source_time"])

        self.assertEqual(event_time.tzinfo, timezone.utc)
        self.assertEqual(event_time.microsecond, 123000)
        self.assertEqual(source_time, datetime(2020, 12, 16, 11, 26, 43, tzinfo=timezone.utc))
        self.assertEqual(event["event_id"], "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1")
        UUID(event["event_id"])
        self.assertEqual(event_time, datetime(2026, 7, 29, 12, 0, 0, 123000, tzinfo=timezone.utc))

    def test_listener_normalizes_legacy_timestamp_alias_without_losing_timezone(self):
        event = {
            "event_id": "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
            "device_id": "vaccine_temperature_simulator",
            "timestamp": "2026-07-29T12:00:00.123+00:00",
            "source_timestamp": "2020-12-16T11:26:43",
            "sensor_name": "Pod1",
            "vaccine_type": "pfizer_ultralow",
            "scenario": "normal",
            "temperature_c": -78.5,
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

        normalized = validate_event(event)

        self.assertEqual(normalized["event_time"], datetime(2026, 7, 29, 12, 0, 0, 123000, tzinfo=timezone.utc))
        self.assertEqual(normalized["source_time"], datetime(2020, 12, 16, 11, 26, 43, tzinfo=timezone.utc))

    def test_source_time_is_optional_for_new_events(self):
        event = {
            "event_id": "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
            "event_time": "2026-07-29T12:00:00.123+00:00",
            "device_id": "vaccine_temperature_simulator",
            "sensor_name": "Pod1",
            "vaccine_type": "pfizer_ultralow",
            "scenario": "normal",
            "temperature_c": -78.5,
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
        normalized = validate_event(event)
        self.assertIsNone(normalized["source_time"])


if __name__ == "__main__":
    unittest.main()
