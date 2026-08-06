# AI worker

This optional, read-only package contains the educational model trainer,
inference service, downloaded Google Colab notebooks, training CSV, generated
model bundle, and ML tests. It does not write PostgreSQL rows or decide
vaccine disposition.

The downloaded notebooks are:

- `iot_data_analysis.ipynb` — IoT sensor/database analysis notebook.
- `Combined notebook.ipynb`, `ML questions Ultralow Vaccine Distribution Data.ipynb`,
  `algorithms.ipynb`, `byteSmart_Ultralow_ML_Questions.ipynb`, `Testing Inference.ipynb`,
  and `Training.ipynb` — downloaded from the project Drive folder.

```bash
python3 -m ai_worker.train_models --vaccine pfizer_ultralow
python3 -m ai_worker.ml_service
```

Generated model artifacts belong in `ai_worker/models/`. The dashboard's
baseline monitoring path works without starting this service.
