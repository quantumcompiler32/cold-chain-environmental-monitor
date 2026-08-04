# Database bootstrap

Run `001_core.sql` against the application database after creating it. It
creates the generic `telemetry_logs` raw-event table and the flattened
`vaccine_temperature_events` table with all timestamp, correlation, and
idempotency indexes. The tables are two projections of one event, linked by
`event_id`; `run_id` is optional grouping metadata.
