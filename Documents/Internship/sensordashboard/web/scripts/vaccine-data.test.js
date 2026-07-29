const assert = require('node:assert/strict');
const test = require('node:test');

const { normalizeEvent, statusLabel, buildScenarioCounts } = require('./vaccine-data.js');

test('normalizes explicit event and source timestamps without changing status', () => {
  const event = normalizeEvent({
    event_id: '2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1',
    event_time: '2026-07-29T12:00:00.123+00:00',
    source_time: '2020-12-16T11:26:43+00:00',
    sensor_name: 'Pod1',
    vaccine_type: 'pfizer_ultralow',
    scenario: 'normal',
    temperature_c: -78.5,
    status: 'STABLE',
  });

  assert.equal(event.event_time, '2026-07-29T12:00:00.123+00:00');
  assert.equal(event.timestamp, event.event_time);
  assert.equal(event.source_time, '2020-12-16T11:26:43+00:00');
  assert.equal(event.status, 'STABLE');
});

test('keeps the mixed scenario phase available to the dashboard', () => {
  const event = normalizeEvent({
    event_id: '2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c2',
    event_time: '2026-07-29T12:00:00.123+00:00',
    sensor_name: 'Pod1',
    vaccine_type: 'pfizer_ultralow',
    scenario: 'mixed',
    scenario_phase: 'cooling_failure',
    temperature_c: -55,
    status: 'TOO_WARM',
  });

  assert.equal(event.scenario, 'mixed');
  assert.equal(event.scenario_phase, 'cooling_failure');
  assert.equal(event.status, 'TOO_WARM');
});

test('uses readable labels for persisted statuses and counts scenarios', () => {
  assert.equal(statusLabel('TOO_WARM'), 'Too warm');
  assert.deepEqual(buildScenarioCounts([
    { scenario: 'normal' },
    { scenario: 'mixed' },
    { scenario: 'mixed' },
  ]), { normal: 1, mixed: 2 });
});
