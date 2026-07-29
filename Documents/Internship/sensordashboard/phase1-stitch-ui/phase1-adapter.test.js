const assert = require('node:assert/strict');
const test = require('node:test');

const { createPhase1Adapter } = require('./phase1-adapter.js');

function event(overrides = {}) {
  return {
    event_id: overrides.event_id ?? 1,
    timestamp: overrides.timestamp ?? '2026-07-29T10:00:00Z',
    sensor_name: overrides.sensor_name ?? 'Pod1',
    vaccine_type: 'pfizer_ultralow',
    scenario: overrides.scenario ?? 'normal',
    temperature_c: overrides.temperature_c ?? -78.5,
    status: overrides.status,
    source_timestamp: overrides.source_timestamp ?? '2020-12-16T11:26:43Z',
  };
}

test('operations view exposes current Pod status and the complete package array', () => {
  const adapter = createPhase1Adapter([
    event({ event_id: 1, sensor_name: 'Pod1', temperature_c: -78.5 }),
    event({ event_id: 2, sensor_name: 'Pod2', temperature_c: -55, scenario: 'failure' }),
  ]);

  const view = adapter.operationsView();

  assert.equal(view.connection, 'connected');
  assert.equal(view.packages.length, 20);
  assert.equal(view.packages[0].name, 'Pod1');
  assert.equal(view.packages[0].status, 'STABLE');
  assert.equal(view.packages[1].status, 'TOO_WARM');
  assert.equal(view.attention[0].name, 'Pod2');
  assert.equal(view.metrics.podsReporting, 2);
  assert.equal(view.metrics.activeExcursions, 1);
});

test('raw events view filters by Pod and keeps newest events first', () => {
  const adapter = createPhase1Adapter([
    event({ event_id: 1, sensor_name: 'Pod1', timestamp: '2026-07-29T10:00:00Z' }),
    event({ event_id: 2, sensor_name: 'Pod2', timestamp: '2026-07-29T10:02:00Z' }),
    event({ event_id: 3, sensor_name: 'Pod1', timestamp: '2026-07-29T10:03:00Z' }),
  ]);

  const view = adapter.rawEventsView({ pod: 'Pod1' });

  assert.equal(view.connection, 'connected');
  assert.deepEqual(view.events.map((item) => item.event_id), ['3', '1']);
  assert.equal(view.totalMatching, 2);
});

test('offline state is explicit and does not invent readings', () => {
  const adapter = createPhase1Adapter([], { connection: 'offline' });

  const operations = adapter.operationsView();
  const raw = adapter.rawEventsView();

  assert.equal(operations.connection, 'offline');
  assert.equal(operations.packages.filter((item) => item.status !== 'UNKNOWN').length, 0);
  assert.equal(raw.connection, 'offline');
  assert.equal(raw.events.length, 0);
});
