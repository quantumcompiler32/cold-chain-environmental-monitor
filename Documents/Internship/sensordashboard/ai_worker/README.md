# AI worker

This optional, read-only package contains the educational model trainer,
inference service, training CSV, generated model bundle, and ML tests. It does
not write PostgreSQL rows or decide vaccine disposition.

```bash
python3 -m ai_worker.train_models --vaccine pfizer_ultralow
python3 -m ai_worker.ml_service
```

Generated model artifacts belong in `ai_worker/models/`. The dashboard's
baseline monitoring path works without starting this service.
