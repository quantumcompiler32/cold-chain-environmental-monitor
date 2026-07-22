import io
import unittest

from analyze_temperature_database import run_analysis


class FakeCursor:
    def __init__(self):
        # Return values follow the report's query order without requiring a
        # live PostgreSQL instance in the unit test.
        self._fetches = [
            (3, 2, "2020-12-16 11:25:54", "2020-12-16 11:26:43", -81.57, -60.25, -75.91, 3, 1, 0),
            [("pfizer_ultralow", "failure", 3), ("pfizer_ultralow", "normal", 0)],
            [("ACCEPTABLE", 2, 66.67), ("TOO_COLD", 1, 33.33)],
            [("Pod1", 2, -81.57, -70.25, -75.91), ("Pod2", 1, -60.25, -60.25, -60.25)],
            [("Pod1", -81.57, "2020-12-16 11:26:43", "TOO_COLD")],
            [("Pod2", -60.25, "2020-12-16 11:25:54", "ACCEPTABLE")],
        ]

    def execute(self, query, params=None):
        return None

    def fetchone(self):
        return self._fetches.pop(0)

    def fetchall(self):
        return self._fetches.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeConnection:
    def cursor(self):
        return FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class AnalysisReportTests(unittest.TestCase):
    def test_report_answers_the_core_temperature_questions(self):
        output = io.StringIO()

        run_analysis(FakeConnection(), printer=lambda line="": output.write(line + "\n"))

        report = output.getvalue()
        self.assertIn("Total Events: 3", report)
        self.assertIn("Total Sensors: 2", report)
        self.assertIn("TOO_COLD", report)
        self.assertIn("33.33%", report)
        self.assertIn("Pod1", report)
        self.assertIn("PROVENANCE SUMMARY", report)
        self.assertIn("failure", report)
        self.assertIn("5 COLDEST READINGS", report)


if __name__ == "__main__":
    unittest.main()
