-- Persistence verification query. Run after a generator/listener demo.
SELECT
    event_id,
    device_id,
    sensor_name AS pod_id,
    vaccine_type,
    scenario,
    temperature_c,
    status,
    event_time,
    received_at,
    stored_at,
    EXTRACT(EPOCH FROM (received_at - event_time)) * 1000 AS ingestion_latency_ms,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - event_time)) AS event_age_seconds
FROM vaccine_temperature_events
ORDER BY event_time DESC, event_id DESC
LIMIT 100;

SELECT
    COUNT(*) AS total_count,
    MIN(event_time) AS first_event_time,
    MAX(event_time) AS latest_event_time
FROM vaccine_temperature_events;
