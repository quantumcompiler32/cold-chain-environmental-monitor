-- Remove the historical CSV timestamp from the live vaccine event contract.
-- New events are current events; the CSV is input guidance only.
BEGIN;

ALTER TABLE vaccine_temperature_events
    DROP COLUMN IF EXISTS source_time;

COMMIT;
