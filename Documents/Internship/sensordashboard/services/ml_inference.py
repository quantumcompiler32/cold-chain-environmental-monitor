"""Small, local-first ML training and inference boundary for the demo.

The module deliberately keeps the model contract independent from PostgreSQL.
Training reads the source CSV once and writes a pickle bundle. Inference only
loads that bundle and scores a submitted Temperature event.
"""

from __future__ import annotations

import csv
import json
import math
import pickle
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MODEL_VERSION = "v1"
MODEL_FILENAME = "model_bundle.pkl"
METADATA_FILENAME = "metadata.json"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "Test1_TempCO2O2.csv"
FEATURE_NAMES = ("hours", "temperature_c", "sensor_spread_c")
MAX_FIT_ROWS = 10_000
PROFILE_DEFAULTS = {
    "pfizer_ultralow": {"target_c": -78.5, "storage_min_c": -80.0, "storage_max_c": -60.0},
    "moderna": {"target_c": -32.5, "storage_min_c": -50.0, "storage_max_c": -15.0},
}
POD_PATTERN = re.compile(r"^Pod\d+$", re.IGNORECASE)


class ModelTrainingError(ValueError):
    """Raised when the source data cannot produce a usable model bundle."""


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _elapsed_hours(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    pieces = text.split(":")
    try:
        if len(pieces) == 3:
            hours, minutes, seconds = (float(piece) for piece in pieces)
            return hours + minutes / 60 + seconds / 3600
        return float(text)
    except ValueError:
        return None


def _parse_event_time(event: dict[str, Any]) -> datetime | None:
    value = event.get("event_time", event.get("timestamp"))
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _csv_training_rows(csv_path: Path) -> list[dict[str, float]]:
    if not csv_path.exists():
        raise ModelTrainingError(f"Training CSV not found: {csv_path}")

    rows: list[dict[str, float]] = []
    with csv_path.open(newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        pod_columns = [name for name in reader.fieldnames or [] if POD_PATTERN.fullmatch(name or "")]
        if not pod_columns:
            raise ModelTrainingError("Training CSV has no Pod temperature columns.")
        for raw in reader:
            temperatures = [_finite(raw.get(column)) for column in pod_columns]
            usable = [value for value in temperatures if value is not None]
            hours = _elapsed_hours(raw.get("Time Elapsed"))
            if hours is None or len(usable) < 2:
                continue
            celsius = [(value - 32.0) * 5.0 / 9.0 for value in usable]
            rows.append({
                "hours": hours,
                "temperature_c": sum(celsius) / len(celsius),
                "sensor_spread_c": max(celsius) - min(celsius),
            })
    if len(rows) < 8:
        raise ModelTrainingError("At least 8 usable Pod rows are required to train the models.")
    return rows


def _linear_fit(rows: list[dict[str, float]]) -> dict[str, Any]:
    points = [(row["hours"], row["temperature_c"]) for row in rows]
    mean_x = sum(point[0] for point in points) / len(points)
    mean_y = sum(point[1] for point in points) / len(points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator if denominator else 0.0
    intercept = mean_y - slope * mean_x
    errors = [abs((intercept + slope * x) - y) for x, y in points]
    return {
        "kind": "linear",
        "algorithm": "linear regression",
        "slope": slope,
        "intercept": intercept,
        "validation": {"metric": "MAE", "value": sum(errors) / len(errors), "unit": "°C"},
        "samples": len(points),
    }


def _standardize(rows: Iterable[tuple[float, ...]]) -> tuple[list[tuple[float, ...]], list[float], list[float]]:
    values = list(rows)
    width = len(values[0])
    means = [sum(row[index] for row in values) / len(values) for index in range(width)]
    scales = []
    for index in range(width):
        variance = sum((row[index] - means[index]) ** 2 for row in values) / len(values)
        scales.append(math.sqrt(variance) or 1.0)
    normalized = [tuple((row[index] - means[index]) / scales[index] for index in range(width)) for row in values]
    return normalized, means, scales


def _logistic_probability(weights: list[float], bias: float, features: tuple[float, ...]) -> float:
    score = bias + sum(weight * feature for weight, feature in zip(weights, features))
    score = max(-40.0, min(40.0, score))
    return 1.0 / (1.0 + math.exp(-score))


def _logistic_fit(rows: list[dict[str, float]], storage_min_c: float, storage_max_c: float) -> dict[str, Any]:
    examples = []
    for row in rows:
        examples.append((
            (row["hours"], row["temperature_c"], row["sensor_spread_c"]),
            int(row["temperature_c"] < storage_min_c or row["temperature_c"] > storage_max_c),
        ))
    labels = [label for _, label in examples]
    if len(set(labels)) < 2:
        raise ModelTrainingError("Training data must contain both in-range and out-of-range Pod readings.")
    normalized, means, scales = _standardize([features for features, _ in examples])
    weights = [0.0] * len(FEATURE_NAMES)
    bias = 0.0
    for _ in range(1800):
        gradients = [0.0] * len(weights)
        bias_gradient = 0.0
        for features, label in zip(normalized, labels):
            error = _logistic_probability(weights, bias, features) - label
            for index, feature in enumerate(features):
                gradients[index] += error * feature
            bias_gradient += error
        rate = 0.12 / len(normalized)
        weights = [weight - rate * gradient for weight, gradient in zip(weights, gradients)]
        bias -= rate * bias_gradient
    predictions = [int(_logistic_probability(weights, bias, features) >= 0.5) for features in normalized]
    accuracy = sum(prediction == label for prediction, label in zip(predictions, labels)) / len(labels)
    return {
        "kind": "logistic",
        "algorithm": "logistic regression",
        "weights": weights,
        "bias": bias,
        "means": means,
        "scales": scales,
        "validation": {"metric": "Accuracy", "value": accuracy, "unit": "ratio"},
        "samples": len(examples),
        "label_definition": f"temperature outside {storage_min_c:g}°C to {storage_max_c:g}°C is out-of-range",
    }


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _kmeans_fit(rows: list[dict[str, float]]) -> dict[str, Any]:
    raw = [(row["temperature_c"], row["sensor_spread_c"]) for row in rows]
    normalized, mins, scales = _standardize(raw)
    cluster_count = min(3, len(normalized))
    centers = [normalized[index * len(normalized) // cluster_count][:] for index in range(cluster_count)]
    assignments = [0] * len(normalized)
    for _ in range(40):
        assignments = [min(range(cluster_count), key=lambda index: _distance(point, tuple(centers[index]))) for point in normalized]
        next_centers = []
        for cluster in range(cluster_count):
            members = [point for point, assignment in zip(normalized, assignments) if assignment == cluster]
            if members:
                columns = list(zip(*members))
                next_centers.append([sum(values) / len(values) for values in columns])
            else:
                next_centers.append(centers[cluster])
        if all(_distance(tuple(old), tuple(new)) < 0.0001 for old, new in zip(centers, next_centers)):
            break
        centers = next_centers
    return {
        "kind": "kmeans",
        "algorithm": "k-means clustering",
        "centers": centers,
        "means": mins,
        "scales": scales,
        "cluster_count": cluster_count,
        "validation": {"metric": "Within-cluster distance", "value": sum(_distance(point, tuple(centers[assignment])) for point, assignment in zip(normalized, assignments)) / len(normalized), "unit": "normalized"},
        "samples": len(normalized),
    }


def train_models(csv_path: str | Path = DEFAULT_CSV, model_dir: str | Path = DEFAULT_MODEL_DIR, vaccine_type: str = "pfizer_ultralow") -> dict[str, Any]:
    """Train the three educational models and save one portable bundle."""
    source = Path(csv_path)
    destination = Path(model_dir)
    try:
        training_profile = PROFILE_DEFAULTS[vaccine_type]
    except KeyError as exc:
        raise ModelTrainingError(f"Unknown vaccine profile: {vaccine_type}") from exc
    rows = _csv_training_rows(source)
    step = max(1, math.ceil(len(rows) / MAX_FIT_ROWS))
    fit_rows = rows[::step]
    bundle = {
        "model_version": MODEL_VERSION,
        "source": source.name,
        "feature_names": list(FEATURE_NAMES),
        "models": {
            "linear": _linear_fit(fit_rows),
            "logistic": _logistic_fit(fit_rows, training_profile["storage_min_c"], training_profile["storage_max_c"]),
            "clustering": _kmeans_fit(fit_rows),
        },
        "training_rows": len(rows),
        "fitted_rows": len(fit_rows),
        "vaccine_type": vaccine_type,
    }
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / MODEL_FILENAME).open("wb") as handle:
        pickle.dump(bundle, handle, protocol=pickle.HIGHEST_PROTOCOL)
    metadata = {
        "model_version": MODEL_VERSION,
        "source": source.name,
        "feature_names": list(FEATURE_NAMES),
        "training_rows": len(rows),
        "fitted_rows": len(fit_rows),
        "vaccine_type": vaccine_type,
        "algorithms": ["linear regression", "logistic regression", "k-means clustering"],
        "educational_use_only": True,
    }
    (destination / METADATA_FILENAME).write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def load_bundle(model_dir: str | Path = DEFAULT_MODEL_DIR) -> dict[str, Any]:
    path = Path(model_dir) / MODEL_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"Model artifacts not found at {path}. Run train_models.py first.")
    with path.open("rb") as handle:
        bundle = pickle.load(handle)
    if bundle.get("model_version") != MODEL_VERSION:
        raise ValueError("Model artifact version is not supported by this service.")
    return bundle


def _profile(event: dict[str, Any]) -> dict[str, float]:
    defaults = PROFILE_DEFAULTS.get(str(event.get("vaccine_type") or "pfizer_ultralow"), PROFILE_DEFAULTS["pfizer_ultralow"])
    return {
        "target_c": _finite(event.get("target_c")) or defaults["target_c"],
        "storage_min_c": _finite(event.get("storage_min_c")) if _finite(event.get("storage_min_c")) is not None else defaults["storage_min_c"],
        "storage_max_c": _finite(event.get("storage_max_c")) if _finite(event.get("storage_max_c")) is not None else defaults["storage_max_c"],
    }


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    temperature = _finite(event.get("temperature_c"))
    if temperature is None:
        raise ValueError("event.temperature_c must be a number")
    if not str(event.get("sensor_name") or "").strip():
        raise ValueError("event.sensor_name is required")
    profile = _profile(event)
    normalized = dict(event)
    normalized["temperature_c"] = temperature
    normalized["storage_min_c"] = profile["storage_min_c"]
    normalized["storage_max_c"] = profile["storage_max_c"]
    normalized["target_c"] = profile["target_c"]
    normalized.setdefault("event_id", "submitted-event")
    if "status" not in normalized:
        normalized["status"] = "TOO_COLD" if temperature < profile["storage_min_c"] else "TOO_WARM" if temperature > profile["storage_max_c"] else "STABLE"
    return normalized


def _feature_vector(event: dict[str, Any], context_events: list[dict[str, Any]]) -> tuple[float, float, float]:
    normalized_context = [_normalize_event(item) for item in context_events] if context_events else []
    all_events = normalized_context + [_normalize_event(event)]
    temperatures = [item["temperature_c"] for item in all_events]
    timestamps = [_parse_event_time(item) for item in all_events]
    valid_times = [item for item in timestamps if item is not None]
    current_time = _parse_event_time(event)
    if current_time is not None and valid_times:
        hours = (current_time - min(valid_times)).total_seconds() / 3600
    else:
        hours = 0.0
    return (hours, temperatures[-1], max(temperatures) - min(temperatures))


def _result_base(model: dict[str, Any], *, status: str, message: str, basis: str) -> dict[str, Any]:
    return {
        "algorithm": model["algorithm"],
        "status": status,
        "message": message,
        "samples": model.get("samples"),
        "validation": model.get("validation"),
        "basis": basis,
    }


def _insufficient(model: dict[str, Any], message: str, basis: str) -> dict[str, Any]:
    return _result_base(model, status="insufficient_data", message=message, basis=basis)


def predict_event(bundle: dict[str, Any], event: dict[str, Any], context_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return advisory model results for one Temperature event."""
    normalized = _normalize_event(event)
    context = context_events or []
    features = _feature_vector(normalized, context)
    models = bundle["models"]

    logistic = models["logistic"]
    scaled = tuple((value - mean) / scale for value, mean, scale in zip(features, logistic["means"], logistic["scales"]))
    probability = _logistic_probability(logistic["weights"], logistic["bias"], scaled)
    logistic_result = _result_base(
        logistic,
        status="ready" if logistic["validation"]["value"] >= 0.6 else "low_confidence",
        message="Investigation probability is available for this event.",
        basis="CSV-trained features: elapsed hours, temperature, and context sensor spread",
    )
    logistic_result["excursionProbability"] = round(probability, 3)
    logistic_result["prediction"] = "investigation-needed" if probability >= 0.5 else "stable-pattern"

    linear = models["linear"]
    if len(context) < 1:
        linear_result = _insufficient(linear, "Add one or more context events for a temperature trend.", "Timestamped temperature context")
    else:
        current_time = _parse_event_time(normalized)
        context_times = [_parse_event_time(item) for item in context]
        valid_context_times = [item for item in context_times if item is not None]
        interval_hours = 0.25
        if current_time is not None and valid_context_times:
            interval_hours = max(0.25, (current_time - max(valid_context_times)).total_seconds() / 3600)
        predicted = normalized["temperature_c"] + linear["slope"] * interval_hours
        linear_result = _result_base(
            linear,
            status="ready" if linear["validation"]["value"] <= 2 else "low_confidence",
            message="Temperature trend estimate is available.",
            basis="CSV-trained temperature trend with submitted event context",
        )
        linear_result["predictedTemperatureC"] = round(predicted, 2)
        linear_result["slopeCPerHour"] = round(linear["slope"], 4)

    clustering = models["clustering"]
    if len({str(item.get("sensor_name")) for item in context + [normalized]}) < 3:
        clustering_result = _insufficient(clustering, "Add readings from at least three Pods for behavior groups.", "Per-Pod temperature and context spread")
    else:
        raw_features = (features[1], features[2])
        scaled_features = tuple((value - mean) / scale for value, mean, scale in zip(raw_features, clustering["means"], clustering["scales"]))
        cluster = min(range(clustering["cluster_count"]), key=lambda index: _distance(scaled_features, tuple(clustering["centers"][index])))
        clustering_result = _result_base(
            clustering,
            status="ready",
            message="Pod behavior group is available.",
            basis="CSV-trained temperature and context spread clusters",
        )
        clustering_result["cluster"] = cluster + 1
        clustering_result["clusterCount"] = clustering["cluster_count"]

    return {
        "model_version": bundle["model_version"],
        "event_id": normalized["event_id"],
        "input": {
            "sensor_name": normalized["sensor_name"],
            "temperature_c": normalized["temperature_c"],
            "vaccine_type": normalized.get("vaccine_type", "pfizer_ultralow"),
            "scenario": normalized.get("scenario", "normal"),
            "storage_min_c": normalized["storage_min_c"],
            "storage_max_c": normalized["storage_max_c"],
            "target_c": normalized["target_c"],
        },
        "features": dict(zip(FEATURE_NAMES, (round(value, 4) for value in features))),
        "read_only": True,
        "educational_use_only": True,
        "primary": logistic_result,
        "secondary": {"linear": linear_result, "clustering": clustering_result},
        "models": {"logistic": logistic_result, "linear": linear_result, "clustering": clustering_result},
    }


def create_app(model_dir: str | Path = DEFAULT_MODEL_DIR):
    """Create the Flask application used by the standalone ML service."""
    try:
        from flask import Flask, jsonify, request
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised in setup failures
        raise RuntimeError("Flask is required. Install sensordashboard/requirements.txt first.") from exc

    app = Flask(__name__)
    try:
        bundle = load_bundle(model_dir)
        load_error = None
    except (FileNotFoundError, ValueError, pickle.UnpicklingError) as exc:
        bundle = None
        load_error = str(exc)

    @app.after_request
    def add_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        payload = {"ok": True, "ready": bundle is not None, "read_only": True, "model_version": bundle.get("model_version") if bundle else None}
        if load_error:
            payload["error"] = load_error
        return jsonify(payload)

    @app.get("/ready")
    def ready():
        payload = {"ok": bundle is not None, "ready": bundle is not None, "read_only": True, "model_version": bundle.get("model_version") if bundle else None}
        if load_error:
            payload["error"] = load_error
        return jsonify(payload), (200 if bundle is not None else 503)

    @app.post("/api/predict")
    def predict():
        if bundle is None:
            return jsonify({"error": load_error or "Model artifacts are unavailable."}), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("event"), dict):
            return jsonify({"error": "Request must contain an event object."}), 400
        try:
            print(f"Event received: {payload['event'].get('event_id', 'submitted-event')}")
            print("Making prediction")
            result = predict_event(bundle, payload["event"], payload.get("context_events") or [])
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        print(f"Prediction: {result['primary'].get('prediction', 'unavailable')} ({result['primary'].get('excursionProbability', 'unavailable')})")
        return jsonify(result)

    return app
