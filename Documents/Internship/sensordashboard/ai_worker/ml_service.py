"""Run the read-only HTTP inference service."""

from __future__ import annotations

import argparse
import os

try:
    from ai_worker.ml_inference import DEFAULT_MODEL_DIR, create_app
except ImportError:  # pragma: no cover - direct script execution
    from ml_inference import DEFAULT_MODEL_DIR, create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the cold-chain ML inference service.")
    parser.add_argument("--host", default=os.environ.get("ML_SERVICE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ML_SERVICE_PORT", "5000")))
    parser.add_argument("--model-dir", default=os.environ.get("ML_MODEL_DIR", str(DEFAULT_MODEL_DIR)))
    args = parser.parse_args()
    app = create_app(args.model_dir)
    print(f"Starting AI ML service on http://{args.host}:{args.port}")
    print(f"Loading model artifacts from {args.model_dir}")
    print("The service is read-only and listens for one-event inference requests.")
    app.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
