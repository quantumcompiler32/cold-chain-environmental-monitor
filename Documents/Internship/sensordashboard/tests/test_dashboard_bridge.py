import unittest
from datetime import datetime, timezone

from services import dashboard_bridge as bridge


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
        "event_id": "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
        "device_id": "vaccine_temperature_simulator",
        "sensor_name": "Pod1",
        "vaccine_type": "pfizer_ultralow",
        "scenario": "normal",
        "scenario_phase": None,
        "occupancy_state": "loaded",
        "batch_id": "Pod1-DEMO-BATCH",
        "cooling_enabled": True,
        "operational_status": "NORMAL",
        "severity": "info",
        "rule_alert": None,
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
        "event_time": datetime(2026, 7, 29, 12, 0, 0, 123000, tzinfo=timezone.utc),
        "received_at": datetime(2026, 7, 29, 12, 0, 1, 456000, tzinfo=timezone.utc),
        "stored_at": datetime(2026, 7, 29, 12, 0, 1, 789000, tzinfo=timezone.utc),
        "ingestion_latency_ms": 1333.0,
        "event_age_seconds": 4.0,
    }
    values.update(overrides)
    return tuple(values[column] for column in bridge.EVENT_COLUMNS)


class DashboardBridgeTests(unittest.TestCase):
    def test_reads_flattened_events_with_explicit_timestamp_semantics(self):
        connection = FakeConnection([database_row()])
        reader = bridge.DatabaseReader(connect_factory=lambda **_: connection, settings={})

        result = reader.fetch_events()

        self.assertEqual(result[0]["event_id"], "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1")
        self.assertEqual(result[0]["timestamp"], "2026-07-29T12:00:00.123000+00:00")
        self.assertNotIn("source_time", result[0])
        self.assertNotIn("source_timestamp", result[0])
        self.assertEqual(result[0]["ingestion_latency_ms"], 1333.0)
        statements = [statement for statement, _ in connection.cursor_instance.statements]
        self.assertIn("SET TRANSACTION READ ONLY", statements[0])
        self.assertTrue(any("vaccine_temperature_events" in statement for statement in statements))
        self.assertNotIn("INSERT", " ".join(statements).upper())

    def test_exports_new_event_columns_deterministically(self):
        connection = FakeConnection([database_row()])
        reader = bridge.DatabaseReader(connect_factory=lambda **_: connection, settings={})

        lines = reader.export_csv().splitlines()

        self.assertEqual(lines[0].split(",")[:4], ["event_id", "device_id", "sensor_name", "vaccine_type"])
        self.assertIn("occupancy_state", lines[0].split(","))
        self.assertIn("operational_status", lines[0].split(","))
        self.assertEqual(len(lines), 2)
        self.assertIn("Pod1", lines[1])

    def test_latest_events_query_is_bounded_and_newest_first(self):
        connection = FakeConnection([database_row()])
        reader = bridge.DatabaseReader(connect_factory=lambda **_: connection, settings={})

        reader.fetch_latest_events()

        statements = [statement for statement, _ in connection.cursor_instance.statements]
        query = statements[-1]
        self.assertIn("ORDER BY event_time DESC, event_id DESC", query)
        self.assertIn("LIMIT 100", query)

    def test_filters_are_parameterized_and_include_scope(self):
        connection = FakeConnection([database_row()])
        reader = bridge.DatabaseReader(connect_factory=lambda **_: connection, settings={})

        result = reader.fetch_events({"pod": "Pod1", "scenario": "normal"})

        query, params = connection.cursor_instance.statements[-1]
        self.assertIn("sensor_name = %s", query)
        self.assertIn("scenario = %s", query)
        self.assertEqual(params, ("Pod1", "normal"))
        self.assertEqual(result[0]["operational_status"], "NORMAL")


if __name__ == "__main__":
    unittest.main()
