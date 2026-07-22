const assert = require('node:assert/strict');
const test = require('node:test');

const {
  PROFILE,
  classifyTemperature,
  parseTemperatureEvents,
  summarizeSensors,
  buildChartSeries,
} = require('../vaccine-data.js');

test('classifies Pfizer ultralow temperatures using the documented profile', () => {
  assert.equal(classifyTemperature(-78.5), 'STABLE');
  assert.equal(classifyTemperature(-79.8), 'ACCEPTABLE');
  assert.equal(classifyTemperature(-80.01), 'TOO_COLD');
  assert.equal(classifyTemperature(-59.99), 'TOO_WARM');
  assert.equal(PROFILE.lowerLimitC, -80);
  assert.equal(PROFILE.upperLimitC, -60);
});

test('parses the temperature project CSV into the dashboard event vocabulary', () => {
  const csv = [
    'id,device_id,event_timestamp,source_timestamp,sensor_name,vaccine_type,scenario,temperature_c,status,received_at',
    '1,device-a,2026-07-22 10:00:00-07,2020-12-16 11:25:54,Pod2,pfizer_ultralow,recovery,-79.7,ACCEPTABLE,2026-07-22 10:00:01-07',
  ].join('\n');
  const [event] = parseTemperatureEvents(csv, 'csv');
  assert.deepEqual(event, {
    device_id: 'device-a',
    timestamp: '2026-07-22 10:00:00-07',
    source_timestamp: '2020-12-16 11:25:54',
    sensor_name: 'Pod2',
    vaccine_type: 'pfizer_ultralow',
    scenario: 'recovery',
    temperature_c: -79.7,
    status: 'ACCEPTABLE',
  });
});

test('summarizes every package sensor and makes the chart series selectable', () => {
  const events = [
    { sensor_name: 'Pod1', temperature_c: -78.5, timestamp: '2026-07-22T10:00:00Z', status: 'STABLE' },
    { sensor_name: 'Pod1', temperature_c: -80.5, timestamp: '2026-07-22T10:01:00Z', status: 'TOO_COLD' },
    { sensor_name: 'Pod2', temperature_c: -59, timestamp: '2026-07-22T10:00:00Z', status: 'TOO_WARM' },
  ];
  const summaries = summarizeSensors(events);
  assert.deepEqual(summaries.map((sensor) => sensor.sensorName), ['Pod1', 'Pod2']);
  assert.equal(summaries[0].latestTemperatureC, -80.5);
  assert.equal(summaries[0].status, 'TOO_COLD');
  assert.equal(summaries[0].excursionCount, 1);

  const chart = buildChartSeries(events, ['Pod1', 'Pod2']);
  assert.deepEqual(chart.labels, ['2026-07-22T10:00:00Z', '2026-07-22T10:01:00Z']);
  assert.deepEqual(chart.series.map((series) => series.sensorName), ['Pod1', 'Pod2']);
  assert.deepEqual(chart.series[0].values, [-78.5, -80.5]);
});
