\set ON_ERROR_STOP on

SELECT 'CREATE DATABASE iot_platform'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'iot_platform'
)\gexec

\connect iot_platform

CREATE TABLE IF NOT EXISTS telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(150) NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    temperature NUMERIC(7, 2),
    humidity NUMERIC(7, 2),
    pressure NUMERIC(9, 2),
    status VARCHAR(30) NOT NULL DEFAULT 'online',
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_telemetry_logs_timestamp
    ON telemetry_logs (timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_telemetry_logs_device_timestamp
    ON telemetry_logs (device_id, timestamp DESC);

CREATE OR REPLACE VIEW v_latest_telemetry AS
SELECT
    id,
    device_id,
    timestamp,
    temperature,
    humidity,
    pressure,
    status,
    received_at
FROM telemetry_logs
ORDER BY timestamp DESC, id DESC;

CREATE OR REPLACE VIEW v_device_summary AS
SELECT
    device_id,
    COUNT(*) AS readings,
    ROUND(AVG(temperature), 2) AS avg_temperature,
    ROUND(AVG(humidity), 2) AS avg_humidity,
    ROUND(AVG(pressure), 2) AS avg_pressure,
    MAX(timestamp) AS latest_reading
FROM telemetry_logs
GROUP BY device_id
ORDER BY device_id;
