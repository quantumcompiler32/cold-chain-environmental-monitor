"""Verify occupancy, severity, alert, and operational-state derivation."""

import unittest
from datetime import datetime, timedelta, timezone

from backend.domain_rules import derive_operational_state


class DomainRuleTests(unittest.TestCase):
    def test_loaded_out_of_range_batch_raises_safety_alert(self):
        result = derive_operational_state({
            "occupancy_state": "loaded",
            "cooling_enabled": True,
            "batch_id": "BATCH-1",
            "status": "TOO_WARM",
        })

        self.assertEqual(result["operational_status"], "CRITICAL")
        self.assertEqual(result["severity"], "critical")
        self.assertEqual(result["rule_alert"], "VACCINE_SAFE_RANGE_VIOLATION")

    def test_empty_chilled_pod_is_energy_waste(self):
        result = derive_operational_state({
            "occupancy_state": "empty",
            "cooling_enabled": True,
            "status": "STABLE",
        })

        self.assertEqual(result["operational_status"], "ENERGY_WASTE")
        self.assertEqual(result["rule_alert"], "EMPTY_POD_COOLING")

    def test_empty_and_offline_are_distinct(self):
        empty = derive_operational_state({"occupancy_state": "empty", "cooling_enabled": False})
        offline = derive_operational_state({"occupancy_state": "offline"})

        self.assertEqual(empty["operational_status"], "EMPTY")
        self.assertEqual(offline["operational_status"], "OFFLINE")

    def test_in_range_recovery_is_explicit(self):
        result = derive_operational_state({
            "occupancy_state": "loaded",
            "cooling_enabled": True,
            "batch_id": "BATCH-1",
            "scenario": "recovery",
            "status": "STABLE",
            "event_time": datetime.now(timezone.utc).isoformat(),
        })

        self.assertEqual(result["operational_status"], "RECOVERY")
        self.assertEqual(result["rule_alert"], "TEMPERATURE_RECOVERY")

    def test_old_event_is_stale(self):
        now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        result = derive_operational_state({
            "occupancy_state": "loaded",
            "cooling_enabled": True,
            "batch_id": "BATCH-1",
            "status": "STABLE",
            "event_time": (now - timedelta(seconds=301)).isoformat(),
        }, now=now)

        self.assertEqual(result["operational_status"], "STALE")
        self.assertEqual(result["severity"], "critical")
        self.assertEqual(result["rule_alert"], "EVENT_STALE")


if __name__ == "__main__":
    unittest.main()
