-- Correlate events emitted by one generator/listener run without replacing
-- event_id, which remains the unique identity of one measurement.
BEGIN;

ALTER TABLE telemetry_logs
    ADD COLUMN IF NOT EXISTS run_id VARCHAR(120);

ALTER TABLE vaccine_temperature_events
    ADD COLUMN IF NOT EXISTS run_id VARCHAR(120);

CREATE INDEX IF NOT EXISTS ix_telemetry_logs_run_id
    ON telemetry_logs (run_id, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_run_id
    ON vaccine_temperature_events (run_id, event_time DESC);

COMMIT;
