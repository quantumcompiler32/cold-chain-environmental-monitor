---
status: accepted
---

# Keep ML inference separate, saved, and read-only

The cold-chain dashboard will use an explicit train-once workflow and a
separately started local inference service. The service loads saved model
artifacts, accepts one Temperature event with optional context, and returns
advisory ML-assisted analysis over HTTP. It does not retrain, persist the
submitted event, or change affected-stock disposition.

## Rationale

Training on every prediction would be slow and would make results harder to
reproduce. A separate service keeps the dashboard integration simple while
preserving the existing PostgreSQL-backed operational workflow. The read-only
boundary also keeps model output from being mistaken for an operational or
clinical decision.

## Consequences

- The model bundle must be trained before the inference service is ready.
- The dashboard can show explicit unavailable, insufficient-data, and
  low-confidence states.
- The service needs a small, documented local HTTP contract and its own
  terminal process.
- Model artifacts are educational and must identify their algorithm, version,
  validation measure, and data basis.
