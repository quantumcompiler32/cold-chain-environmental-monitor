const assert = require('node:assert/strict');
const test = require('node:test');

const { normalizeEvent, statusLabel, operationalStatusLabel, buildScenarioCounts, scenarioDisplayLabel, buildPodSummary, buildChartSeries } = require('./vaccine-data.js');

function podEvent(eventId, eventTime, temperature, overrides = {}) {
  return normalizeEvent({
    event_id: String(eventId),
    event_time: eventTime,
    sensor_name: 'Pod1',
    vaccine_type: 'pfizer_ultralow',
    temperature_c: temperature,
    batch_id: 'DEMO-BATCH',
    ...overrides,
  });
}

test('normalizes event timestamps without importing a CSV source timestamp', () => {
  const event = normalizeEvent({
    event_id: '2f6f7c3d-5bd5-4f8c-9b8b-5bdb81f8d0c1',
    event_time: '2026-07-29T12:00:00.123+00:00',
    sensor_name: 'Pod1',
    vaccine_type: 'pfizer_ultralow',
    scenario: 'normal',
    temperature_c: -78.5,
    status: 'STABLE',
  });

  assert.equal(event.event_time, '2026-07-29T12:00:00.123+00:00');
  assert.equal(event.timestamp, event.event_time);
  assert.equal(event.source_time, undefined);
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
  assert.equal(scenarioDisplayLabel(event.scenario_phase), 'Cooling failure');
});

test('uses readable labels for persisted statuses and counts scenarios', () => {
  assert.equal(statusLabel('TOO_WARM'), 'Too warm');
  assert.equal(operationalStatusLabel('ENERGY_WASTE'), 'Energy waste');
  assert.equal(operationalStatusLabel('OFFLINE'), 'Offline');
  assert.deepEqual(buildScenarioCounts([
    { scenario: 'normal' },
    { scenario: 'mixed' },
    { scenario: 'mixed' },
  ]), { normal: 1, mixed: 2 });
  assert.deepEqual(buildScenarioCounts([
    { scenario: 'mixed', scenario_phase: 'normal' },
    { scenario: 'mixed', scenario_phase: 'recovery' },
    { scenario: 'mixed', scenario_phase: 'recovery' },
  ]), { normal: 1, recovery: 2 });
});

test('describes a rapid warming trend and recommends reviewing the cause', () => {
  const summary = buildPodSummary([
    podEvent(1, '2026-07-29T12:00:00Z', -78.5),
    podEvent(2, '2026-07-29T12:05:00Z', -78.2),
    podEvent(3, '2026-07-29T12:15:00Z', -77.8),
  ]);

  assert.equal(summary.trendKey, 'rapid_warming');
  assert.equal(summary.trendMessage, 'Temperature is rising quickly');
  assert.equal(summary.recommendation, 'Review door activity and inspect cooling');
  assert.equal(summary.chartWindowMinutes, 60);
});

test('describes a Pod recovering after a warm excursion', () => {
  const summary = buildPodSummary([
    podEvent(1, '2026-07-29T12:00:00Z', -55, { status: 'TOO_WARM' }),
    podEvent(2, '2026-07-29T12:02:00Z', -62),
    podEvent(3, '2026-07-29T12:04:00Z', -70),
  ]);

  assert.equal(summary.trendKey, 'recovering');
  assert.equal(summary.trendMessage, 'Temperature is moving back toward the safe range');
  assert.equal(summary.recommendation, 'Monitor recovery until the temperature stabilizes');
});

test('returns to stable after recovery holds inside the range', () => {
  const summary = buildPodSummary([
    podEvent(1, '2026-07-29T12:00:00Z', -55, { status: 'TOO_WARM' }),
    podEvent(2, '2026-07-29T12:05:00Z', -61),
    podEvent(3, '2026-07-29T12:15:00Z', -61.1),
  ]);

  assert.equal(summary.trendKey, 'stable');
  assert.equal(summary.trendMessage, 'Temperature is stable');
});

test('flags an empty Pod that is still being cooled as energy waste', () => {
  const summary = buildPodSummary([
    podEvent(1, '2026-07-29T12:00:00Z', -78.5, {
      occupancy_state: 'empty',
      batch_id: '',
    }),
  ]);

  assert.equal(summary.operationalStatus, 'ENERGY_WASTE');
  assert.equal(summary.trendMessage, 'Pod is empty while cooling is active');
  assert.equal(summary.recommendation, 'Consider standby mode');
});

test('aggregates dense chart input into a readable number of points', () => {
  const events = Array.from({ length: 200 }, (_, index) => podEvent(
    index,
    new Date(Date.UTC(2026, 6, 29, 12, 0, index)).toISOString(),
    -78.5 + (index % 2 ? 0.4 : -0.2),
  ));

  const chart = buildChartSeries(events, ['Pod1'], { maxPoints: 40 });

  assert.equal(chart.labels.length, 40);
  assert.equal(chart.series[0].values.length, 40);
  assert.ok(chart.series[0].values.every(Number.isFinite));
});
