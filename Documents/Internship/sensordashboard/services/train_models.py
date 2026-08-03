"""Train and persist the educational cold-chain model bundle."""

from __future__ import annotations

import argparse
import json

try:
    from services.ml_inference import DEFAULT_CSV, DEFAULT_MODEL_DIR, train_models
except ImportError:  # pragma: no cover - direct script execution
    from ml_inference import DEFAULT_CSV, DEFAULT_MODEL_DIR, train_models


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the cold-chain ML models once and save their artifacts.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Pod CSV used for training.")
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR), help="Directory where model artifacts are saved.")
    parser.add_argument("--vaccine", choices=("pfizer_ultralow", "moderna"), default="pfizer_ultralow", help="Profile whose range defines the training label.")
    args = parser.parse_args()
    print(json.dumps(train_models(args.csv, args.model_dir, args.vaccine), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
