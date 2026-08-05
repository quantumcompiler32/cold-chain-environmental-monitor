"""Verify the optional local ML bundle and its explicit data-boundary rules."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ai_worker.ml_inference import create_app, load_bundle, predict_event, train_models


def write_training_csv(path: Path) -> None:
    rows = [
        ["date", "time", "Time Elapsed", "Pod1", "Pod2", "Pod3", "O2", "CO2"],
        ["", "", "", "b1", "b2", "b3", "O2", "CO2"],
        ["", "", "", "F", "F", "F", "%", "%"],
    ]
    for index in range(30):
        base = -109.0 + index * 0.25
        if index in {10, 20}:
            base -= 15
        rows.append(["16-Dec-20", "11:25:54", f"0:00:{index:02d}", base, base + 0.5, base - 0.5, 40, 60])
    with path.open("w", newline="") as handle:
        csv.writer(handle).writerows(rows)


def event(**overrides):
    value = {
        "event_id": "event-1",
        "event_time": "2026-08-03T12:00:00Z",
        "sensor_name": "Pod1",
        "vaccine_type": "pfizer_ultralow",
        "scenario": "normal",
        "temperature_c": -78.5,
        "storage_min_c": -80.0,
        "storage_max_c": -60.0,
        "status": "STABLE",
    }
    value.update(overrides)
    return value


class ModelTrainingTests(unittest.TestCase):
    def test_training_creates_loadable_artifacts_and_predictions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path = root / "training.csv"
            model_dir = root / "models"
            write_training_csv(csv_path)

            summary = train_models(csv_path, model_dir)
            bundle = load_bundle(model_dir)
            result = predict_event(bundle, event())

            self.assertEqual(summary["model_version"], "v1")
            self.assertEqual(bundle["model_version"], "v1")
            self.assertEqual(summary["vaccine_type"], "pfizer_ultralow")
            self.assertEqual(result["primary"]["algorithm"], "logistic regression")
            self.assertIn(result["primary"]["status"], {"ready", "low_confidence", "insufficient_data"})
            self.assertTrue((model_dir / "model_bundle.pkl").exists())
            self.assertTrue((model_dir / "metadata.json").exists())


class InferenceHttpTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        csv_path = root / "training.csv"
        write_training_csv(csv_path)
        train_models(csv_path, root / "models")
        self.client = create_app(root / "models").test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_health_reports_loaded_models(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ready"])
        self.assertEqual(response.json["model_version"], "v1")

    def test_ready_reports_loaded_models(self):
        response = self.client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ready"])

    def test_predict_returns_advisory_results_for_one_event(self):
        response = self.client.post("/api/predict", json={"event": event()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["model_version"], "v1")
        self.assertEqual(response.json["primary"]["algorithm"], "logistic regression")
        self.assertIn("secondary", response.json)
        self.assertEqual(response.json["input"]["sensor_name"], "Pod1")
        self.assertEqual(response.json["features"]["temperature_c"], -78.5)
        self.assertTrue(response.json["read_only"])

    def test_predict_rejects_missing_event_without_writing_data(self):
        response = self.client.post("/api/predict", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("event", response.json["error"])

    def test_predict_supports_dashboard_cors_preflight(self):
        response = self.client.options("/api/predict")

        self.assertEqual(response.status_code, 200)
        self.assertIn("POST", response.headers["Access-Control-Allow-Methods"])
        self.assertEqual(response.headers["Access-Control-Allow-Headers"], "Content-Type")


if __name__ == "__main__":
    unittest.main()
