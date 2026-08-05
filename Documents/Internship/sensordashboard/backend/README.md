# Backend

The backend owns event generation, MQTT subscription, PostgreSQL persistence,
the read-only dashboard bridge, and non-ML backend tests. The normal database
writer is `temperature_subscriber.py` when started with `--write-db`.

Run modules from the project root so Python resolves the `backend` package:

```bash
python3 -m backend.temperature_subscriber --write-db --output-mode verbose
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario normal --count 6
python3 -m backend.dashboard_bridge
```
