"""Run opt-in PostgreSQL integration checks against the configured local DB."""

import os
import unittest
from datetime import datetime, timezone

import psycopg

from services.dashboard_bridge import DatabaseReader
from services.temperature_subscriber import persist_event, postgres_settings


@unittest.skipUnless(os.environ.get("RUN_DB_INTEGRATION") == "1", "set RUN_DB_INTEGRATION=1 for a local PostgreSQL integration run")
class DatabasePipelineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            connection = psycopg.connect(**postgres_settings())
            connection.close()
        except Exception as exc:
            raise unittest.SkipTest(f"local PostgreSQL is unavailable: {exc}")

    def test_real_database_supports_atomic_write_and_readiness_read(self):
        event = {
            "event_id": "7f7f64be-93b5-4aa8-9de8-7bcad7b5f1d2",
            "run_id": "integration-rollback-run",
            "device_id": "integration-test",
            "event_time": datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc),
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
            "measurement_confidence": "integration test",
        }

        class RollbackConnection:
            def __enter__(self):
                self.connection = psycopg.connect(**postgres_settings())
                return self.connection

            def __exit__(self, exc_type, exc, traceback):
                self.connection.rollback()
                self.connection.close()
                return False

        result = persist_event(event, connection_factory=RollbackConnection)

        self.assertEqual(result.event_id, event["event_id"])
        self.assertEqual(result.run_id, event["run_id"])
        self.assertFalse(result.duplicate)
        reader = DatabaseReader(settings=postgres_settings())
        reader.check()


if __name__ == "__main__":
    unittest.main()
