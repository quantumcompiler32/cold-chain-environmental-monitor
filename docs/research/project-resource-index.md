# Project resource index

This index records where the project materials belong under the requested
packaging convention.

| Resource | Location | Reason |
| --- | --- | --- |
| Dashboard HTML, JavaScript, CSS, and browser tests | `frontend/` | UI-only dashboard assets |
| PostgreSQL schema, migrations, reset, verification, and tests | `db/` | Database assets |
| Event generator, MQTT subscriber, bridge, and backend tests | `backend/` | Non-UI middleware/backend |
| Model code, model bundle, training CSV, downloaded Colab notebooks, and ML tests | `ai_worker/` | Colab-derived and ML/AI workflow |
| Arduino/sensor images and hardware notes | `edge/` | Edge/hardware reference material |
| Project paper and research URLs | `docs/research/` | Research and supporting paper |
| PowerPoint and Google Slides access note | `docs/presentation/` | Presentation deliverables |
| Dataset notes | `docs/datasets/` | Dataset documentation; canonical CSV remains in `ai_worker/data/` |
| Runbooks, architecture, data dictionary, and database notes | `docs/` | Generated project documentation |

## Colab and Drive status

The specified Drive project folder supplied the Colab notebooks, three model
artifacts, the `14888121` dataset archive, the dataset paper PDF, and research
documents. Colab notebooks and models are in `ai_worker/`; the archive is in
`docs/datasets/`; and research documents are in `docs/research/`. The local
repository also retains the canonical `Test1_TempCO2O2.csv` and existing
presentation materials.
