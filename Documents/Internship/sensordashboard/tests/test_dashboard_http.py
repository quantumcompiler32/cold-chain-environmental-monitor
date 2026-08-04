import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from services.dashboard_bridge import DashboardHandler, DatabaseUnavailable


class StubReader:
    def __init__(self, *, ready=True):
        self.ready = ready
        self.check_calls = 0

    def check(self):
        self.check_calls += 1
        if not self.ready:
            raise DatabaseUnavailable("database is offline")


class DashboardHttpIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.reader = StubReader()
        DashboardHandler.reader = self.reader
        self.server = None
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        except PermissionError:
            self.skipTest("sandbox does not permit localhost socket binding")
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        if self.server is None:
            return
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, method, path):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        connection.request(method, path, headers={"X-Request-ID": "http-test-1"})
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response, json.loads(body)

    def test_health_is_liveness_and_ready_checks_database(self):
        response, payload = self.request("GET", "/health")

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["database_checked"])
        self.assertEqual(self.reader.check_calls, 0)

        response, payload = self.request("GET", "/ready")

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ready"])
        self.assertEqual(self.reader.check_calls, 1)

    def test_readiness_reports_503_when_database_is_unavailable(self):
        self.reader.ready = False

        response, payload = self.request("GET", "/api/health")

        self.assertEqual(response.status, 503)
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["request_id"], "http-test-1")

    def test_route_discovery_and_structured_404_explain_port_boundary(self):
        response, payload = self.request("GET", "/")
        self.assertEqual(response.status, 200)
        self.assertIn("/api/events", payload["routes"])

        response, payload = self.request("GET", "/pages/domain-vaccine.html")
        self.assertEqual(response.status, 404)
        self.assertEqual(payload["path"], "/pages/domain-vaccine.html")
        self.assertIn("website port", payload["hint"])
        self.assertEqual(response.getheader("X-Request-ID"), "http-test-1")

    def test_mutation_methods_are_rejected_by_read_only_bridge(self):
        response, payload = self.request("POST", "/api/events")

        self.assertEqual(response.status, 405)
        self.assertEqual(response.getheader("Allow"), "GET, OPTIONS")
        self.assertEqual(payload["request_id"], "http-test-1")


if __name__ == "__main__":
    unittest.main()
