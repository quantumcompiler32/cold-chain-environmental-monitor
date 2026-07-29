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
    sensor_tolerance_c DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    temperature_min_possible_c DOUBLE PRECISION,
    temperature_max_possible_c DOUBLE PRECISION,
    storage_min_c DOUBLE PRECISION,
    storage_max_c DOUBLE PRECISION,
    uncertainty_status VARCHAR(30) NOT NULL DEFAULT 'WITHIN_RANGE',
    boundary_crossing BOOLEAN NOT NULL DEFAULT FALSE,
    measurement_confidence VARCHAR(160) NOT NULL DEFAULT 'Approximately +/-0.5 C Type-T thermocouple accuracy',
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add the provenance fields when upgrading an older version of this table.
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS vaccine_type VARCHAR(50) NOT NULL DEFAULT 'pfizer_ultralow';
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS scenario VARCHAR(30) NOT NULL DEFAULT 'normal';

-- Safe additive migration for tables that already contain events. These are
-- derived fields; temperature_c and status are deliberately not rewritten.
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS sensor_tolerance_c DOUBLE PRECISION NOT NULL DEFAULT 0.5;
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS temperature_min_possible_c DOUBLE PRECISION;
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS temperature_max_possible_c DOUBLE PRECISION;
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS storage_min_c DOUBLE PRECISION;
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS storage_max_c DOUBLE PRECISION;
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS uncertainty_status VARCHAR(30) NOT NULL DEFAULT 'WITHIN_RANGE';
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS boundary_crossing BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE temperature_events
    ADD COLUMN IF NOT EXISTS measurement_confidence VARCHAR(160) NOT NULL DEFAULT 'Approximately +/-0.5 C Type-T thermocouple accuracy';

-- Backfill legacy rows with the Pfizer range. Existing measured values and
-- original statuses remain unchanged.
UPDATE temperature_events
SET temperature_min_possible_c = temperature_c - sensor_tolerance_c,
    temperature_max_possible_c = temperature_c + sensor_tolerance_c,
    storage_min_c = COALESCE(storage_min_c, -80.0),
    storage_max_c = COALESCE(storage_max_c, -60.0)
WHERE temperature_min_possible_c IS NULL
   OR temperature_max_possible_c IS NULL
   OR storage_min_c IS NULL
   OR storage_max_c IS NULL;

UPDATE temperature_events
SET boundary_crossing = (
        temperature_min_possible_c < storage_min_c
        AND temperature_max_possible_c >= storage_min_c
    ) OR (
        temperature_min_possible_c <= storage_max_c
        AND temperature_max_possible_c > storage_max_c
    )
WHERE temperature_min_possible_c IS NOT NULL
  AND temperature_max_possible_c IS NOT NULL
  AND storage_min_c IS NOT NULL
  AND storage_max_c IS NOT NULL;

ALTER TABLE temperature_events
    ALTER COLUMN temperature_min_possible_c SET DEFAULT 0,
    ALTER COLUMN temperature_max_possible_c SET DEFAULT 0,
    ALTER COLUMN storage_min_c SET DEFAULT -80.0,
    ALTER COLUMN storage_max_c SET DEFAULT -60.0;

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

CREATE INDEX IF NOT EXISTS ix_temperature_events_uncertainty_status
    ON temperature_events(uncertainty_status);
