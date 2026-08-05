"""Verify the canonical SQL bootstrap and verification assets are coherent."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DatabaseAssetTests(unittest.TestCase):
    def test_clean_bootstrap_is_canonical_and_keeps_vaccine_fields_out_of_raw_table(self):
        sql = (ROOT / "database" / "bootstrap" / "001_core.sql").read_text()
        self.assertIn("CREATE TABLE IF NOT EXISTS telemetry_logs", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS vaccine_temperature_events", sql)
        self.assertIn("event_time TIMESTAMPTZ", sql)
        self.assertIn("received_at TIMESTAMPTZ", sql)
        self.assertIn("stored_at TIMESTAMPTZ", sql)
        self.assertIn("run_id VARCHAR(120)", sql)
        for field in ("occupancy_state", "batch_id", "cooling_enabled", "operational_status", "severity", "rule_alert"):
            self.assertIn(field, sql)
        self.assertNotIn("ALTER TABLE", sql)
        self.assertNotIn("source_time", sql)
        raw_definition = sql.split("CREATE TABLE IF NOT EXISTS vaccine_temperature_events", 1)[0]
        self.assertNotIn("vaccine_type", raw_definition)
        self.assertNotIn("scenario VARCHAR", raw_definition)

    def test_latest_event_verification_includes_latency_age_and_bounds(self):
        sql = (ROOT / "database" / "verification" / "latest_events.sql").read_text()
        for field in ("event_id", "sensor_name", "vaccine_type", "scenario", "event_time", "received_at", "ingestion_latency_ms", "event_age_seconds"):
            self.assertIn(field, sql)
        self.assertIn("COUNT(*)", sql)
        self.assertIn("MIN(event_time)", sql)
        self.assertIn("MAX(event_time)", sql)
        self.assertIn("run_id", sql)

    def test_fast_verifier_checks_read_only_schema_and_projection_parity(self):
        script = (ROOT / "scripts" / "verify_database.py").read_text()

        self.assertIn("SET TRANSACTION READ ONLY", script)
        self.assertIn("orphan_generic_count", script)
        self.assertIn("orphan_domain_count", script)
        self.assertIn("latest_run_id", script)


if __name__ == "__main__":
    unittest.main()
