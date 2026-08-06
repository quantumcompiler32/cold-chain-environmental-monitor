# Backend

The backend owns event generation, MQTT subscription, PostgreSQL persistence,
the read-only dashboard bridge, and end-to-end pipeline verification. The
normal database writer is `temperature_subscriber.py` when started with
`--write-db`.

Run modules from the project root so Python resolves the `backend` package:

```bash
python3 -m backend.temperature_subscriber --write-db --output-mode verbose
python3 -m backend.temperature_event_generator --sensor Pod1 --scenario normal --count 6
python3 -m backend.dashboard_bridge
```

## File guide

| File | Purpose |
|---|---|
| `__init__.py` | Marks `backend` as a Python package. |
| `event_contract.py` | Standardizes timestamp parsing, UTC conversion, and formatting. |
| `domain_rules.py` | Converts event facts into operational statuses, severities, and alerts. |
| `temperature_uncertainty.py` | Calculates sensor tolerance ranges and boundary-crossing status. |
| `temperature_event_generator.py` | Reads CSV variation, creates simulated events, and publishes them to MQTT. |
| `temperature_subscriber.py` | Validates MQTT events, writes both PostgreSQL projections, and sends `NOTIFY`. |
| `dashboard_bridge.py` | Provides read-only HTTP APIs, CSV export, and live SSE updates from PostgreSQL. |
| `terminal_output.py` | Formats readable service and event messages for the terminal. |
| `e2e_verify.py` | Verifies the complete generator-to-dashboard pipeline. |
| `e2e_scenarios.json` | Defines the scenarios and expected results for E2E verification. |
