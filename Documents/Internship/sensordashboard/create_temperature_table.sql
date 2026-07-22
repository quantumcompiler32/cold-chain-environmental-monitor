CREATE TABLE IF NOT EXISTS temperature_events
(
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    source_timestamp TIMESTAMP NULL,
    sensor_name VARCHAR(100) NOT NULL,
    vaccine_type VARCHAR(50) NOT NULL DEFAULT 'pfizer_ultralow',
    scenario VARCHAR(30) NOT NULL DEFAULT 'normal',
    temperature_c DOUBLE PRECISION NOT NULL,
    status VARCHAR(30) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add the provenance fields when upgrading an older version of this table.
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS vaccine_type VARCHAR(50) NOT NULL DEFAULT 'pfizer_ultralow';
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS scenario VARCHAR(30) NOT NULL DEFAULT 'normal';

CREATE INDEX IF NOT EXISTS ix_temperature_events_event_timestamp
    ON temperature_events(event_timestamp);

CREATE INDEX IF NOT EXISTS ix_temperature_events_sensor_name
    ON temperature_events(sensor_name);

CREATE INDEX IF NOT EXISTS ix_temperature_events_status
    ON temperature_events(status);

CREATE INDEX IF NOT EXISTS ix_temperature_events_vaccine_type
    ON temperature_events(vaccine_type);

CREATE INDEX IF NOT EXISTS ix_temperature_events_scenario
    ON temperature_events(scenario);
