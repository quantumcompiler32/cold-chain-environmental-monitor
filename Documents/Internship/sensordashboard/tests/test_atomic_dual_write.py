import json
import unittest
from datetime import datetime, timezone

from services.temperature_subscriber import persist_event, process_message


EVENT = {
    "event_id": "2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1",
    "device_id": "vaccine_temperature_simulator",
    "event_time": datetime(2026, 7, 29, 12, 0, 0, 123000, tzinfo=timezone.utc),
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


class FakeCursor:
    def __init__(self, duplicate=False, fail_on_statement=None):
        self.statements = []
        self.duplicate = duplicate
        self.fail_on_statement = fail_on_statement

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if self.fail_on_statement == len(self.statements):
            raise RuntimeError("vaccine insert failed")

    def fetchone(self):
        return None if self.duplicate else (EVENT["event_id"],)


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True
        return False

    def cursor(self):
        return self.cursor_instance


class AtomicDualWriteTests(unittest.TestCase):
    def test_listener_captures_received_at_before_persistence(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)
        clock_values = iter((
            datetime(2026, 7, 29, 12, 0, 0, 111111, tzinfo=timezone.utc),
            datetime(2026, 7, 29, 12, 0, 0, 222222, tzinfo=timezone.utc),
        ))

        process_message(
            json.dumps(EVENT, default=str),
            connection_factory=lambda: connection,
            clock=lambda: next(clock_values),
        )

        generic_params = cursor.statements[0][1]
        self.assertEqual(generic_params[-2].microsecond, 111000)
        self.assertEqual(generic_params[-1].microsecond, 222000)

    def test_success_writes_generic_and_vaccine_rows_in_one_transaction(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)

        result = persist_event(
            EVENT,
            connection_factory=lambda: connection,
            clock=lambda: datetime(2026, 7, 29, 12, 0, 0, 456789, tzinfo=timezone.utc),
        )

        self.assertEqual(result.event_id, EVENT["event_id"])
        self.assertFalse(result.duplicate)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)
        self.assertEqual(len(cursor.statements), 2)
        generic_params = cursor.statements[0][1]
        vaccine_params = cursor.statements[1][1]
        self.assertEqual(generic_params[0], vaccine_params[0])
        self.assertEqual(generic_params[-1], vaccine_params[-1])
        self.assertEqual(generic_params[-1].microsecond, 456000)

    def test_failure_rolls_back_both_writes(self):
        cursor = FakeCursor(fail_on_statement=2)
        connection = FakeConnection(cursor)

        with self.assertRaisesRegex(RuntimeError, "vaccine insert failed"):
            persist_event(
                EVENT,
                connection_factory=lambda: connection,
                clock=lambda: datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc),
            )

        self.assertFalse(connection.committed)
        self.assertTrue(connection.rolled_back)
        self.assertEqual(len(cursor.statements), 2)

    def test_duplicate_event_is_reported_idempotently(self):
        cursor = FakeCursor(duplicate=True)
        connection = FakeConnection(cursor)

        result = persist_event(
            EVENT,
            connection_factory=lambda: connection,
            clock=lambda: datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(result.duplicate)
        self.assertIsNone(result.stored_at)
        self.assertTrue(connection.committed)
        self.assertFalse(connection.rolled_back)


if __name__ == "__main__":
    unittest.main()
