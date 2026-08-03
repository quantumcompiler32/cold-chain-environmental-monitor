-- Called by db/scripts/reset_demo.py only after its environment and confirmation
-- guards pass.
BEGIN;
DROP TABLE IF EXISTS vaccine_temperature_events CASCADE;
DROP TABLE IF EXISTS telemetry_logs CASCADE;
DROP TABLE IF EXISTS temperature_events CASCADE;
COMMIT;
