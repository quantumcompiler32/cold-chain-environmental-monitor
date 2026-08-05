"""Keep the dashboard Makefile lifecycle contract safe and discoverable."""

import re
import unittest
from pathlib import Path


MAKEFILE = Path(__file__).resolve().parents[2] / "Makefile"


def target_body(text: str, target: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(target)}:\n(?P<body>.*?)(?=^\S[^\n]*:\n|\Z)", text)
    if not match:
        raise AssertionError(f"missing Make target: {target}")
    return match.group("body")


class DashboardMakefileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.makefile = MAKEFILE.read_text()

    def test_start_dashboard_records_a_project_local_pid_and_runs_in_background(self):
        body = target_body(self.makefile, "start-dashboard")

        self.assertIn("DASHBOARD_RUNTIME_DIR ?= .runtime", self.makefile)
        self.assertIn("dashboard_bridge.pid", self.makefile)
        self.assertIn("backend.dashboard_bridge", body)
        self.assertIn("new_pid=$$!", body)
        self.assertIn("echo \"$$new_pid\" > \"$$pid_file\"", body)

    def test_stop_dashboard_verifies_command_before_sigterm_and_never_kills_by_port(self):
        body = target_body(self.makefile, "stop-dashboard")

        self.assertIn("ps -p \"$$pid\" -o command=", body)
        self.assertIn("backend.dashboard_bridge", body)
        self.assertIn('kill -TERM "$$pid"', body)
        self.assertIn('rm -f "$$pid_file"', body)
        self.assertNotRegex(body, r"(?:lsof|fuser|pkill).*(?:8787|port)")

    def test_watch_dashboard_is_a_separate_sse_client(self):
        body = target_body(self.makefile, "watch-dashboard")

        self.assertIn("/ready", body)
        self.assertIn("curl -N", body)
        self.assertIn("/api/live/stream", body)
        self.assertNotIn("nohup $(PYTHON) -m backend.dashboard_bridge", body)


if __name__ == "__main__":
    unittest.main()
