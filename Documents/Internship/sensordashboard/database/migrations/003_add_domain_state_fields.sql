-- Add the non-ML domain state needed for pod occupancy and rule alerts.
BEGIN;

ALTER TABLE vaccine_temperature_events
    ADD COLUMN IF NOT EXISTS occupancy_state VARCHAR(20) NOT NULL DEFAULT 'loaded',
    ADD COLUMN IF NOT EXISTS batch_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS cooling_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS operational_status VARCHAR(30) NOT NULL DEFAULT 'NORMAL',
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20) NOT NULL DEFAULT 'info',
    ADD COLUMN IF NOT EXISTS rule_alert VARCHAR(80);

CREATE INDEX IF NOT EXISTS ix_vaccine_events_batch_event_time
    ON vaccine_temperature_events (batch_id, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_occupancy_event_time
    ON vaccine_temperature_events (occupancy_state, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_severity_event_time
    ON vaccine_temperature_events (severity, event_time DESC);

COMMIT;
