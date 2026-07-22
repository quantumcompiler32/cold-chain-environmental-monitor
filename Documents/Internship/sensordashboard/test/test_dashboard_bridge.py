import importlib.util
import unittest
from pathlib import Path


# Resolve the bridge beside the dashboard so this test still works after the
# whole folder is uploaded to another machine or cloned from GitHub.
BRIDGE_PATH = Path(__file__).resolve().parents[1] / "dashboard_bridge.py"
SPEC = importlib.util.spec_from_file_location("dashboard_bridge", BRIDGE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bridge)


def base_request(**overrides):
    request = {
        "profile": "pfizer_ultralow",
        "scenario": "outlier",
        "sensors": ["Pod1", "Pod3", "Pod11"],
        "interval_ms": 500,
        "max_events": 20,
        "save_to_database": False,
        "min_temp": None,
        "max_temp": None,
    }
    request.update(overrides)
    return request


class DashboardBridgeTests(unittest.TestCase):
    def test_validates_multiple_pods_and_normalizes_duplicates(self):
        # Duplicate Pod buttons should not create duplicate generator children.
        result = bridge.validate_start_request(base_request(sensors=["Pod1", "Pod1", "Pod20"]))
        assert result["sensors"] == ["Pod1", "Pod20"]

    def test_requires_custom_bounds_for_moderna(self):
        # The UI supplies suggested values, but the bridge still validates the
        # final values at the HTTP boundary.
        with self.assertRaisesRegex(ValueError, "Moderna"):
            bridge.validate_start_request(base_request(profile="moderna"))

        result = bridge.validate_start_request(base_request(profile="moderna", min_temp=-35, max_temp=-25))
        assert result["profile"]["target_c"] == -32.5
        assert result["profile"]["min_c"] == -35.0

    def test_rejects_invalid_run_controls(self):
        # Reject bad controls before starting any subprocess.
        with self.assertRaisesRegex(ValueError, "interval_ms"):
            bridge.validate_start_request(base_request(interval_ms=25))
        with self.assertRaisesRegex(ValueError, "Invalid Pod"):
            bridge.validate_start_request(base_request(sensors=["Ambient"]))

    def test_builds_one_generator_command_per_selected_pod(self):
        # One selected Pod maps to one generator command.
        request = bridge.validate_start_request(base_request())
        command = bridge.build_generator_command(request, "Pod11", Path("/project/temperature_event_generator.py"))
        assert command[-10:] == [
            "--sensor", "Pod11",
            "--vaccine-type", "pfizer_ultralow",
            "--scenario", "outlier",
            "--interval-ms", "500",
            "--max-events", "20",
        ]

    def test_publishes_event_to_subscriber_with_unique_sequence(self):
        # The sequence survives identical source timestamps and tags active
        # run events without changing the existing event fields.
        state = bridge.DashboardState(Path("/tmp"), Path("/tmp/temperature_event_generator.py"))
        subscriber = state.add_subscriber()
        subscriber.get_nowait()  # Initial status message.
        state.publish_event({
            "device_id": "device",
            "timestamp": "2026-07-22T10:00:00Z",
            "source_timestamp": "2020-12-16T11:25:54Z",
            "sensor_name": "Pod1",
            "vaccine_type": "pfizer_ultralow",
            "scenario": "outlier",
            "temperature_c": -78.5,
            "status": "STABLE",
        })
        payload = subscriber.get_nowait()
        assert payload["type"] == "event"
        assert payload["event"]["event_sequence"] == 1
        assert "run_id" not in payload["event"]
        state.run = {"running": True, "run_id": "run-1"}
        state.publish_event({"sensor_name": "Pod1", "temperature_c": -78.0})
        running_payload = subscriber.get_nowait()
        assert running_payload["event"]["run_id"] == "run-1"
        assert running_payload["event"]["event_sequence"] == 2
        state.mqtt_client.disconnect()


if __name__ == "__main__":
    unittest.main()
