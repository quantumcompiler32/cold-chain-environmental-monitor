import unittest

from services.domain_rules import derive_operational_state


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


if __name__ == "__main__":
    unittest.main()
