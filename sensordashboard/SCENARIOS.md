# Generator scenarios

Run scenarios from the terminal. The dashboard only reads the rows after the
subscriber stores them in PostgreSQL.

- `normal`: ordinary variation around the selected profile.
- `outlier`: adds an intentional out-of-range reading.
- `failure`: keeps readings above the selected maximum.
- `recovery`: moves readings toward the selected target.

Example:

```bash
source .venv/bin/activate
python3 temperature_event_generator.py \
  --sensor Pod1 \
  --vaccine-type pfizer_ultralow \
  --scenario outlier \
  --interval-ms 500 \
  --max-events 20
```
