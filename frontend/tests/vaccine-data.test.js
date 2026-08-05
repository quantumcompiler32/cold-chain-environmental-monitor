/* Purpose: test event normalization, filters, units, aggregation, and averages. */
const assert = require('node:assert/strict');
const test = require('node:test');

const {
  normalizeEvent,
  statusLabel,
  operationalStatusLabel,
  buildScenarioCounts,
  scenarioDisplayLabel,
  buildPodSummary,
  buildChartSeries,
  getDateRange,
  formatTemperature,
  formatLocalDateTime,
  formatAxisTimestamp,
  buildPhaseTrail,
  buildActiveAlerts,
  aggregateTemperatureSeries,
  movingAverage,
} = require('../scripts/vaccine-data.js');

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

test('builds daily, weekly, monthly, and custom date ranges from a fixed local date', () => {
  const now = new Date('2026-08-04T15:30:00-07:00');

  assert.deepEqual(getDateRange('daily', now), {
    start: '2026-08-04T07:00:00.000Z',
    end: '2026-08-04T22:30:00.000Z',
  });
  assert.deepEqual(getDateRange('weekly', now), {
    start: '2026-08-03T07:00:00.000Z',
    end: '2026-08-04T22:30:00.000Z',
  });
  assert.deepEqual(getDateRange('monthly', now), {
    start: '2026-08-01T07:00:00.000Z',
    end: '2026-08-04T22:30:00.000Z',
  });
  assert.deepEqual(getDateRange('custom', now, {
    start: '2026-07-29T09:00',
    end: '2026-07-30T17:00',
  }), {
    start: '2026-07-29T16:00:00.000Z',
    end: '2026-07-31T00:00:00.000Z',
  });
});

test('formats temperature in the selected unit and labels the chart timezone', () => {
  assert.equal(formatTemperature(-40, 'C'), '−40.0°C');
  assert.equal(formatTemperature(-40, 'F'), '−40.0°F');
  assert.equal(formatTemperature(null, 'F'), '—');
  assert.equal(formatAxisTimestamp('2026-08-04T19:30:00Z', {
    timeZone: 'America/Los_Angeles',
    locale: 'en-US',
  }), 'Aug 4, 12:30 PM PDT');
});

test('formats persisted timestamps in the selected local display timezone', () => {
  assert.equal(formatLocalDateTime('2026-07-15T16:00:00Z', {
    timeZone: 'America/Los_Angeles',
    locale: 'en-US',
  }), 'Jul 15, 9:00:00 AM PDT');
});

test('builds an ordered phase trail for mixed sensor history', () => {
  assert.deepEqual(buildPhaseTrail([
    podEvent(1, '2026-07-15T10:00:00Z', -78.5, { scenario: 'mixed', scenario_phase: 'normal' }),
    podEvent(2, '2026-07-15T10:01:00Z', -55, { scenario: 'mixed', scenario_phase: 'cooling_failure' }),
    podEvent(3, '2026-07-15T10:02:00Z', -78.5, { scenario: 'mixed', scenario_phase: 'recovery' }),
  ]), ['Normal', 'Cooling failure', 'Recovery']);
});

test('keeps the latest temperature separate from active alert history and exposes follow-up readings', () => {
  const alerts = buildActiveAlerts([
    podEvent(1, '2026-07-15T10:00:00Z', -78.5),
    podEvent(2, '2026-07-15T10:01:00Z', -55, { status: 'TOO_WARM', severity: 'critical', rule_alert: 'VACCINE_SAFE_RANGE_VIOLATION' }),
    podEvent(3, '2026-07-15T10:02:00Z', -62, { status: 'TOO_WARM', severity: 'critical', rule_alert: 'VACCINE_SAFE_RANGE_VIOLATION' }),
  ]);

  assert.equal(alerts.length, 1);
  assert.equal(alerts[0].podId, 'Pod1');
  assert.equal(alerts[0].severity, 'critical');
  assert.equal(alerts[0].event.event_id, '2');
  assert.deepEqual(alerts[0].subsequentReadings.map((event) => event.event_id), ['3']);
});

test('does not keep a resolved alert active after a newer safe reading', () => {
  assert.deepEqual(buildActiveAlerts([
    podEvent(1, '2026-07-15T10:00:00Z', -55, { status: 'TOO_WARM', severity: 'critical' }),
    podEvent(2, '2026-07-15T10:01:00Z', -78.5, { status: 'STABLE', severity: 'info', rule_alert: '' }),
  ]), []);
});

test('aggregates explicit hourly intervals and computes a three-point trailing average', () => {
  const events = [
    podEvent(1, '2026-08-04T00:05:00Z', -78),
    podEvent(2, '2026-08-04T00:55:00Z', -77),
    podEvent(3, '2026-08-04T01:10:00Z', -76),
    podEvent(4, '2026-08-04T02:10:00Z', -75),
  ];
  const series = aggregateTemperatureSeries(events, ['Pod1'], { interval: 'hour', movingAverageWindow: 3 });

  assert.deepEqual(series.labels, [
    '2026-08-04T00:00:00.000Z',
    '2026-08-04T01:00:00.000Z',
    '2026-08-04T02:00:00.000Z',
  ]);
  assert.deepEqual(series.series[0].values, [-77.5, -76, -75]);
  assert.deepEqual(series.series[0].movingAverage, [-77.5, -76.75, -76.16666666666667]);
  assert.equal(series.definition, 'Hourly buckets; each value is the arithmetic mean of readings in each hour; times display in local time.');
  assert.equal(series.movingAverageDefinition, 'Trailing 3-point moving average of aggregated interval means; the current point and up to 2 prior points are averaged.');
  assert.deepEqual(movingAverage([1, 2, 3, 4], 3), [1, 1.5, 2, 3]);
});

test('keeps latest recorded temperature separate from period average', () => {
  const summary = require('../scripts/vaccine-data.js').summarizeSensors([
    podEvent(1, '2026-08-04T00:00:00Z', -78),
    podEvent(2, '2026-08-04T01:00:00Z', -74),
  ])[0];

  assert.equal(summary.latestTemperatureC, -74);
  assert.equal(summary.averageTemperatureC, -76);
  assert.notEqual(summary.latestTemperatureC, summary.averageTemperatureC);
});
