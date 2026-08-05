-- Canonical clean bootstrap for the local/demo vaccine monitor.
-- This file is intentionally complete. Additive schema changes belong in
-- db/migrations/, not in the clean bootstrap path.

BEGIN;

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    run_id VARCHAR(120),
    device_id VARCHAR(150) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    temperature NUMERIC(7, 2),
    humidity NUMERIC(7, 2),
    pressure NUMERIC(9, 2),
    status VARCHAR(30) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS vaccine_temperature_events (
    event_id UUID PRIMARY KEY REFERENCES telemetry_logs(event_id) ON DELETE CASCADE,
    run_id VARCHAR(120),
    device_id VARCHAR(150) NOT NULL,
    sensor_name VARCHAR(100) NOT NULL,
    vaccine_type VARCHAR(80) NOT NULL,
    scenario VARCHAR(30) NOT NULL,
    scenario_phase VARCHAR(30),
    occupancy_state VARCHAR(20) NOT NULL DEFAULT 'loaded',
    batch_id VARCHAR(120),
    cooling_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    operational_status VARCHAR(30) NOT NULL DEFAULT 'NORMAL',
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    rule_alert VARCHAR(80),
    temperature_c NUMERIC(8, 3) NOT NULL,
    status VARCHAR(30) NOT NULL,
    sensor_tolerance_c NUMERIC(8, 3) NOT NULL,
    temperature_min_possible_c NUMERIC(8, 3) NOT NULL,
    temperature_max_possible_c NUMERIC(8, 3) NOT NULL,
    storage_min_c NUMERIC(8, 3) NOT NULL,
    storage_max_c NUMERIC(8, 3) NOT NULL,
    uncertainty_status VARCHAR(40) NOT NULL,
    boundary_crossing BOOLEAN NOT NULL,
    measurement_confidence VARCHAR(180) NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_telemetry_logs_event_time
    ON telemetry_logs (event_time DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_telemetry_logs_device_event_time
    ON telemetry_logs (device_id, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_telemetry_logs_received_at
    ON telemetry_logs (received_at DESC);
CREATE INDEX IF NOT EXISTS ix_telemetry_logs_run_id
    ON telemetry_logs (run_id, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_event_time
    ON vaccine_temperature_events (event_time DESC, event_id);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_sensor_event_time
    ON vaccine_temperature_events (sensor_name, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_scenario_event_time
    ON vaccine_temperature_events (scenario, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_status_event_time
    ON vaccine_temperature_events (status, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_vaccine_event_time
    ON vaccine_temperature_events (vaccine_type, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_received_at
    ON vaccine_temperature_events (received_at DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_run_id
    ON vaccine_temperature_events (run_id, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_batch_event_time
    ON vaccine_temperature_events (batch_id, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_occupancy_event_time
    ON vaccine_temperature_events (occupancy_state, event_time DESC);
CREATE INDEX IF NOT EXISTS ix_vaccine_events_severity_event_time
    ON vaccine_temperature_events (severity, event_time DESC);

COMMIT;
