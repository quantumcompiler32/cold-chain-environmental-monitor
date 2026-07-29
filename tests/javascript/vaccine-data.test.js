const assert = require('node:assert/strict');
const test = require('node:test');

const { normalizeEvent, statusLabel, summarize } = require('../../web/scripts/vaccine-data.js');

test('normalizes a stored PostgreSQL event without changing its status', () => {
  const event = normalizeEvent({
    event_id: 7,
    event_timestamp: '2026-07-23T10:00:00Z',
    sensor_name: 'Pod1',
    vaccine_type: 'pfizer_ultralow',
    scenario: 'normal',
    temperature_c: -78.5,
    status: 'STABLE',
  });

  assert.equal(event.event_id, '7');
  assert.equal(event.vaccine_label, 'Pfizer ultralow');
  assert.equal(event.status, 'STABLE');
  assert.equal(event.storage_min_c, -80);
});

test('derives a missing status from the stored profile bounds', () => {
  assert.equal(normalizeEvent({ vaccine_type: 'pfizer_ultralow', temperature_c: -81 }).status, 'TOO_COLD');
  assert.equal(normalizeEvent({ vaccine_type: 'pfizer_ultralow', temperature_c: -59 }).status, 'TOO_WARM');
  assert.equal(normalizeEvent({ vaccine_type: 'moderna', temperature_c: -32.5 }).status, 'STABLE');
});

test('summarizes all database events for the dashboard', () => {
  const summary = summarize([
    normalizeEvent({ sensor_name: 'Pod1', temperature_c: -78, status: 'STABLE', timestamp: '2026-07-23T10:00:00Z' }),
    normalizeEvent({ sensor_name: 'Pod1', temperature_c: -81, status: 'TOO_COLD', timestamp: '2026-07-23T10:01:00Z' }),
    normalizeEvent({ sensor_name: 'Pod2', temperature_c: -59, status: 'TOO_WARM', timestamp: '2026-07-23T10:02:00Z' }),
  ]);

  assert.equal(summary.total, 3);
  assert.equal(summary.sensors, 2);
  assert.equal(summary.outOfRange, 2);
  assert.equal(summary.statuses.STABLE, 1);
  assert.equal(summary.statuses.TOO_COLD, 1);
  assert.equal(summary.statuses.TOO_WARM, 1);
  assert.equal(summary.latest.sensor_name, 'Pod2');
});

test('uses concise dashboard status labels', () => {
  assert.equal(statusLabel('STABLE'), 'In range');
  assert.equal(statusLabel('TOO_COLD'), 'Too cold');
});
