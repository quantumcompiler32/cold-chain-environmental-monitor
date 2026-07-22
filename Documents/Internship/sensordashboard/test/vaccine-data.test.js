const assert = require('node:assert/strict');
const test = require('node:test');

const {
  PROFILE,
  classifyTemperature,
  parseTemperatureEvents,
  summarizeSensors,
  buildChartSeries,
  getChartHeight,
  createDemoEvents,
  buildStatusCounts,
  getProfile,
  normalizeEvent,
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
    event_id: '2026-07-22 10:00:01-07',
    device_id: 'device-a',
    timestamp: '2026-07-22 10:00:00-07',
    received_at: '2026-07-22 10:00:01-07',
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

test('imports the wide experiment CSV with Pod Fahrenheit columns', () => {
  const csv = [
    'date,time,Time Elapsed,Pod1,Pod2,Ambient',
    ',,,b1,b2,Toutside',
    ',,,F,F,F',
    '16-Dec-20,11:25:54,0:00:00,-113.7838,-113.4706,71.7494',
    '16-Dec-20,11:26:12,0:00:18,-111.98,-112.1,71.7',
  ].join('\n');
  const events = parseTemperatureEvents(csv, 'csv');
  assert.equal(events.length, 4);
  assert.deepEqual([...new Set(events.map((event) => event.sensor_name))], ['Pod1', 'Pod2']);
  assert.equal(events[0].temperature_c, -80.99);
  assert.equal(events[0].status, 'TOO_COLD');
});

test('demo events visibly include both sides of the safety range', () => {
  const counts = buildStatusCounts(createDemoEvents());
  assert.ok(counts.TOO_COLD > 0);
  assert.ok(counts.TOO_WARM > 0);
  const summaries = summarizeSensors(createDemoEvents());
  assert.equal(summaries.find((sensor) => sensor.sensorName === 'Pod3').status, 'TOO_COLD');
  assert.equal(summaries.find((sensor) => sensor.sensorName === 'Pod11').status, 'TOO_WARM');
});

test('chart height grows with the number of selected Pods', () => {
  assert.ok(getChartHeight(6) > getChartHeight(1));
  assert.equal(getChartHeight(0), getChartHeight(1));
});

test('classifies Moderna events using custom bounds', () => {
  const profile = getProfile('moderna', { min_temp: -35, max_temp: -25 });
  assert.equal(normalizeEvent({ sensor_name: 'Pod4', timestamp: '2026-07-22T10:00:00Z', temperature_c: -30 }, profile).status, 'STABLE');
  assert.equal(normalizeEvent({ sensor_name: 'Pod4', timestamp: '2026-07-22T10:00:01Z', temperature_c: -36 }, profile).status, 'TOO_COLD');
  assert.equal(normalizeEvent({ sensor_name: 'Pod4', timestamp: '2026-07-22T10:00:02Z', temperature_c: -24 }, profile).status, 'TOO_WARM');
});

test('chart keeps repeated live timestamps as separate points', () => {
  const events = [
    { event_id: '1', sensor_name: 'Pod1', temperature_c: -78, timestamp: '2026-07-22T10:00:00Z' },
    { event_id: '2', sensor_name: 'Pod1', temperature_c: -77, timestamp: '2026-07-22T10:00:00Z' },
    { event_id: '3', sensor_name: 'Pod2', temperature_c: -79, timestamp: '2026-07-22T10:00:00Z' },
  ];
  const chart = buildChartSeries(events, ['Pod1', 'Pod2']);
  assert.equal(chart.labels.length, 2);
  assert.deepEqual(chart.series[0].values, [-78, -77]);
  assert.deepEqual(chart.series[1].values, [-79, null]);
});
