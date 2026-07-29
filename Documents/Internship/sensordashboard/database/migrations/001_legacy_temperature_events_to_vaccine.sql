-- Upgrade path for the experimental legacy table. Run this only when
-- preserving existing rows matters; clean demos should use reset_demo.py.
BEGIN;

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
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
    device_id VARCHAR(150) NOT NULL,
    sensor_name VARCHAR(100) NOT NULL,
    vaccine_type VARCHAR(80) NOT NULL,
    scenario VARCHAR(30) NOT NULL,
    scenario_phase VARCHAR(30),
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
    source_time TIMESTAMPTZ,
    event_time TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL
);

INSERT INTO telemetry_logs (
    event_id, device_id, topic, event_time, payload, temperature, status,
    received_at, stored_at
)
SELECT
    md5(id::text)::uuid,
    device_id,
    'devices/temperature',
    event_timestamp,
    jsonb_build_object(
        'event_id', md5(id::text)::uuid,
        'device_id', device_id,
        'event_time', event_timestamp,
        'source_time', source_timestamp,
        'sensor_name', sensor_name,
        'vaccine_type', vaccine_type,
        'scenario', scenario,
        'temperature_c', temperature_c,
        'status', status
    ),
    temperature_c,
    status,
    received_at,
    received_at
FROM temperature_events
ON CONFLICT (event_id) DO NOTHING;

INSERT INTO vaccine_temperature_events (
    event_id, device_id, sensor_name, vaccine_type, scenario, temperature_c,
    status, sensor_tolerance_c, temperature_min_possible_c,
    temperature_max_possible_c, storage_min_c, storage_max_c,
    uncertainty_status, boundary_crossing, measurement_confidence,
    source_time, event_time, received_at, stored_at
)
SELECT
    md5(id::text)::uuid,
    device_id,
    sensor_name,
    vaccine_type,
    scenario,
    temperature_c,
    status,
    sensor_tolerance_c,
    COALESCE(temperature_min_possible_c, temperature_c - sensor_tolerance_c),
    COALESCE(temperature_max_possible_c, temperature_c + sensor_tolerance_c),
    COALESCE(storage_min_c, -80.0),
    COALESCE(storage_max_c, -60.0),
    uncertainty_status,
    boundary_crossing,
    measurement_confidence,
    source_timestamp AT TIME ZONE 'UTC',
    event_timestamp,
    received_at,
    received_at
FROM temperature_events
ON CONFLICT (event_id) DO NOTHING;

COMMIT;
