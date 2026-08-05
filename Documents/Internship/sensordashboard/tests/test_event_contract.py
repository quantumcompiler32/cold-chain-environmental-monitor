"""Verify event IDs, UTC timestamps, and wire-format normalization."""

import unittest
from datetime import datetime, timezone
from uuid import UUID

from services.temperature_event_generator import make_event, resolve_profile
from services.temperature_subscriber import validate_event


class EventContractTests(unittest.TestCase):
    def test_generated_event_uses_current_utc_time_without_csv_time(self):
        event = make_event(
            "Pod1",
            {
                "temperature_c": -78.5,
            },
            resolve_profile("pfizer_ultralow"),
            "normal",
            event_number=1,
            total_events=1,
            event_id="2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
            run_id="run-2026-08-04-a",
            event_time=datetime(2026, 7, 29, 12, 0, 0, 123456, tzinfo=timezone.utc),
        )
        event_time = datetime.fromisoformat(event["event_time"])
        self.assertEqual(event_time.tzinfo, timezone.utc)
        self.assertEqual(event_time.microsecond, 123000)
        self.assertNotIn("source_time", event)
        self.assertNotIn("source_timestamp", event)
        self.assertEqual(event["event_id"], "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1")
        self.assertEqual(event["run_id"], "run-2026-08-04-a")
        UUID(event["event_id"])
        self.assertEqual(event_time, datetime(2026, 7, 29, 12, 0, 0, 123000, tzinfo=timezone.utc))

    def test_listener_ignores_legacy_csv_timestamp_alias(self):
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
        self.assertNotIn("source_time", normalized)
        self.assertNotIn("source_timestamp", normalized)


if __name__ == "__main__":
    unittest.main()
