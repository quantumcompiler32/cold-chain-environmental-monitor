import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "dashboard_bridge.py"
SPEC = importlib.util.spec_from_file_location("dashboard_bridge", BRIDGE_PATH)
bridge = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bridge)


class FakeCursor:
    description = [(column,) for column in bridge.EVENT_COLUMNS]

    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        self.statements.append((statement, params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_instance


def database_row(**overrides):
    values = {
        "id": 7,
        "device_id": "device-a",
        "event_timestamp": datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc),
        "source_timestamp": datetime(2020, 12, 16, 11, 25, 54),
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
        "received_at": datetime(2026, 7, 23, 10, 0, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return tuple(values[column] for column in bridge.EVENT_COLUMNS)


class DashboardBridgeTests(unittest.TestCase):
    def test_reads_events_using_a_read_only_transaction(self):
        connection = FakeConnection([database_row()])
        reader = bridge.DatabaseReader(connect_factory=lambda **_: connection, settings={})

        result = reader.fetch_events()

        self.assertEqual(result[0]["event_id"], "7")
        self.assertEqual(result[0]["timestamp"], "2026-07-23T10:00:00+00:00")
        self.assertEqual(result[0]["temperature_c"], -78.5)
        statements = [statement for statement, _ in connection.cursor_instance.statements]
        self.assertIn("SET TRANSACTION READ ONLY", statements[0])
        self.assertIn("SELECT", statements[1])
        self.assertNotIn("INSERT", " ".join(statements).upper())

    def test_exports_all_database_events_with_dashboard_headers(self):
        connection = FakeConnection([database_row(), database_row(id=8, sensor_name="Pod2")])
        reader = bridge.DatabaseReader(connect_factory=lambda **_: connection, settings={})

        csv_text = reader.export_csv()

        lines = csv_text.splitlines()
        self.assertEqual(lines[0].split(",")[0], "event_id")
        self.assertEqual(len(lines), 3)
        self.assertIn('Pod1', lines[1])
        self.assertIn('Pod2', lines[2])

    def test_database_failure_is_reported_without_writing(self):
        def fail_connect(**_):
            raise RuntimeError("database offline")

        reader = bridge.DatabaseReader(connect_factory=fail_connect, settings={})

        with self.assertRaisesRegex(bridge.DatabaseUnavailable, "database offline"):
            reader.fetch_events()


if __name__ == "__main__":
    unittest.main()
