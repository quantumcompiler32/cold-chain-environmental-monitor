"""Verify deterministic generator scenarios, counts, and phase metadata."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from backend.temperature_event_generator import (
    expand_sensor_names,
    load_temperature_data,
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

    def test_outlier_is_an_isolated_out_of_range_scenario(self):
        values = [
            transform_temperature(-78.5, self.profile, "outlier", index, 6)
            for index in range(1, 7)
        ]

        self.assertEqual(values[0], self.profile.min_c - 1.0)
        self.assertEqual(values[1], self.profile.max_c + 1.0)
        self.assertTrue(
            all(
                value < self.profile.min_c or value > self.profile.max_c
                for value in values
            )
        )

    def test_warning_stays_in_range_but_crosses_sensor_uncertainty_boundary(self):
        event = make_event(
            "Pod1",
            self.row,
            self.profile,
            "warning",
            event_number=1,
            total_events=1,
            event_time=self.event_time,
            batch_id="DEMO-BATCH",
        )

        self.assertEqual(event["status"], "ACCEPTABLE")
        self.assertEqual(event["operational_status"], "WARNING")
        self.assertEqual(event["severity"], "warning")
        self.assertEqual(event["rule_alert"], "TEMPERATURE_BOUNDARY_RISK")

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

    def test_cli_accepts_outlier_without_a_seed(self):
        with patch.object(sys, "argv", ["generator", "--scenario", "outlier", "--count", "9", "--output-mode", "summary", "--vaccine", "pfizer_ultralow"]):
            args = parse_arguments()
        self.assertEqual(args.scenario, "outlier")
        self.assertEqual(args.count, 9)
        self.assertIsNone(args.seed)
        self.assertEqual(args.output_mode, "summary")

    def test_cli_accepts_multiple_pods_in_one_run(self):
        with patch.object(
            sys,
            "argv",
            ["generator", "--sensor", "Pod1", "Pod2", "Pod3", "--count", "9"],
        ):
            args = parse_arguments()

        self.assertEqual(args.sensor, ["Pod1", "Pod2", "Pod3"])

    def test_cli_accepts_comma_separated_pods(self):
        with patch.object(
            sys,
            "argv",
            ["generator", "--sensor", "Pod1,Pod2", "Pod3", "--count", "9"],
        ):
            args = parse_arguments()

        self.assertEqual(args.sensor, ["Pod1", "Pod2", "Pod3"])

    def test_cli_accepts_all_sensor_selector(self):
        with patch.object(sys, "argv", ["generator", "--sensor", "ALL", "--count", "1"]):
            args = parse_arguments()

        self.assertEqual(args.sensor, ["ALL"])

    def test_all_sensor_selector_discovers_numeric_pod_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "temperatures.csv"
            csv_path.write_text("Pod10,Ambient,Pod2,Pod1\n32,40,33,34\n", encoding="utf-8")

            sensors = expand_sensor_names(["ALL"], csv_path)

        self.assertEqual(sensors, ["Pod1", "Pod2", "Pod10"])

    def test_cli_accepts_reproducible_backdated_start_time(self):
        with patch.object(
            sys,
            "argv",
            ["generator", "--start-time", "2026-07-15T09:00:00-07:00", "--count", "2"],
        ):
            args = parse_arguments()

        self.assertEqual(
            args.start_time,
            datetime(2026, 7, 15, 16, 0, 0, tzinfo=timezone.utc),
        )

    def test_cli_accepts_local_start_time_without_timezone_offset(self):
        local_value = datetime(2026, 7, 21, 10, 40).astimezone().astimezone(timezone.utc)
        with patch.object(
            sys,
            "argv",
            ["generator", "--start-time", "2026-07-21T10:40:00", "--count", "2"],
        ):
            args = parse_arguments()

        self.assertEqual(args.start_time, local_value)

    def test_backdated_run_marks_ingestion_clock_without_changing_event_shape(self):
        event = make_event(
            "Pod1",
            self.row,
            self.profile,
            "normal",
            event_number=1,
            total_events=1,
            event_time=self.event_time,
            backdate_ingestion=True,
        )

        self.assertEqual(event["_simulated_at"], event["event_time"])
        self.assertEqual(event["timestamp"], event["event_time"])

    def test_main_publishes_each_round_to_every_selected_pod(self):
        class PublishResult:
            rc = 0

            def wait_for_publish(self):
                return None

        class FakeClient:
            def __init__(self):
                self.messages = []

            def connect(self, *_args):
                return None

            def loop_start(self):
                return None

            def publish(self, _topic, payload, qos=0):
                self.messages.append(json.loads(payload))
                return PublishResult()

            def loop_stop(self):
                return None

            def disconnect(self):
                return None

        fake_client = FakeClient()
        pod_readings = pd.DataFrame({"temperature_c": [-78.5, -78.4]})

        with patch.object(
            sys,
            "argv",
            [
                "generator",
                "--sensor",
                "Pod1",
                "Pod2",
                "--count",
                "2",
                "--interval-ms",
                "0",
                "--output-mode",
                "none",
            ],
        ), patch(
            "backend.temperature_event_generator.mqtt.Client",
            return_value=fake_client,
        ), patch(
            "backend.temperature_event_generator.load_temperature_data",
            side_effect=[("Pod1", pod_readings), ("Pod2", pod_readings)],
        ):
            from backend.temperature_event_generator import main

            self.assertEqual(main(), 0)

        self.assertEqual(
            [event["sensor_name"] for event in fake_client.messages],
            ["Pod1", "Pod2", "Pod1", "Pod2"],
        )

    def test_write_db_mode_does_not_also_publish_to_mqtt(self):
        pod_readings = pd.DataFrame({"temperature_c": [-78.5]})
        persisted = []

        def fake_persist(event, **_kwargs):
            persisted.append(event)
            return SimpleNamespace(duplicate=False, stored_at=None)

        with patch.object(
            sys,
            "argv",
            ["generator", "--count", "1", "--interval-ms", "0", "--output-mode", "none", "--write-db", "--run-id", "run-direct"],
        ), patch(
            "backend.temperature_event_generator.mqtt.Client",
        ) as mqtt_client, patch(
            "backend.temperature_event_generator.load_temperature_data",
            return_value=("Pod1", pod_readings),
        ), patch(
            "backend.temperature_subscriber.persist_event",
            side_effect=fake_persist,
        ):
            from backend.temperature_event_generator import main

            self.assertEqual(main(), 0)

        mqtt_client.assert_not_called()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["run_id"], "run-direct")

    def test_csv_temperature_guidance_does_not_require_or_import_a_timestamp(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "temperatures.csv"
            csv_path.write_text("Pod1\n32\n50\n", encoding="utf-8")

            sensor_name, readings = load_temperature_data(csv_path, "Pod1")

        self.assertEqual(sensor_name, "Pod1")
        self.assertEqual(list(readings.columns), ["temperature_f", "temperature_c"])
        self.assertNotIn("source_timestamp", readings.columns)


if __name__ == "__main__":
    unittest.main()
