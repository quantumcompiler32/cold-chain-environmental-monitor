import unittest
import sys
from datetime import datetime, timezone
from unittest.mock import patch

from services.terminal_output import format_event_block
from services.temperature_subscriber import parse_arguments


EVENT = {
    "event_id": "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
    "device_id": "vaccine_temperature_simulator",
    "sensor_name": "Pod1",
    "vaccine_type": "pfizer_ultralow",
    "scenario": "mixed",
    "scenario_phase": "recovery",
    "temperature_c": -78.5,
    "status": "STABLE",
    "storage_min_c": -80.0,
    "storage_max_c": -60.0,
    "uncertainty_status": "WITHIN_RANGE",
    "boundary_crossing": False,
    "measurement_confidence": "Approximately +/-0.5 C Type-T thermocouple accuracy",
    "event_time": "2026-07-29T12:00:00.123+00:00",
    "source_time": "2020-12-16T11:26:43.000+00:00",
}


class TerminalOutputTests(unittest.TestCase):
    def test_event_block_is_readable_and_contains_pipeline_fields(self):
        output = format_event_block(
            EVENT,
            component="LISTENER",
            outcome="PERSISTED",
            sequence=3,
            topic="devices/temperature",
            received_at=datetime(2026, 7, 29, 12, 0, 0, 140000, tzinfo=timezone.utc),
            stored_at=datetime(2026, 7, 29, 12, 0, 0, 142000, tzinfo=timezone.utc),
        )

        self.assertIn("[LISTENER] PERSISTED #0003", output)
        self.assertIn("scenario      : mixed / recovery", output)
        self.assertIn("temperature   : -78.50 °C", output)
        self.assertIn("event_time    : 2026-07-29T12:00:00.123+00:00", output)
        self.assertIn("received_at   : 2026-07-29T12:00:00.140+00:00", output)
        self.assertIn("stored_at     : 2026-07-29T12:00:00.142+00:00", output)
        self.assertIn("topic         : devices/temperature", output)

    def test_subscriber_defaults_to_live_verbose_output(self):
        with patch.object(sys, "argv", ["subscriber", "--write-db"]):
            args = parse_arguments()

        self.assertEqual(args.output_mode, "verbose")


if __name__ == "__main__":
    unittest.main()
