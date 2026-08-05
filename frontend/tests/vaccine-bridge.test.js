/* Purpose: test the bridge's URL construction and read-only client behavior. */
const assert = require('node:assert/strict');
const test = require('node:test');

const { buildExportPath, mergeEventSets } = require('../scripts/vaccine-bridge.js');

test('exports the currently selected dashboard scope as CSV', () => {
  assert.equal(buildExportPath({
    start: '2026-08-01T00:00:00.000Z',
    end: '2026-08-04T00:00:00.000Z',
    pod: 'Pod 1',
    vaccine: 'pfizer_ultralow',
  }), '/api/events/export.csv?start=2026-08-01T00%3A00%3A00.000Z&end=2026-08-04T00%3A00%3A00.000Z&pod=Pod+1&vaccine=pfizer_ultralow');
});

test('exports all events when no dashboard scope is selected', () => {
  assert.equal(buildExportPath({}), '/api/events/export.csv');
});

test('merges persisted recent events with forward-only live events without duplicates', () => {
  const persisted = [
    { event_id: 'old', event_time: '2026-07-29T12:00:00Z' },
    { event_id: 'same', event_time: '2026-07-29T12:01:00Z', temperature_c: -78.5 },
  ];
  const live = [
    { event_id: 'same', event_time: '2026-07-29T12:01:00Z', temperature_c: -78.2 },
    { event_id: 'new', event_time: '2026-07-29T12:02:00Z' },
  ];

  assert.deepEqual(mergeEventSets(persisted, live), [
    { event_id: 'old', event_time: '2026-07-29T12:00:00Z' },
    { event_id: 'same', event_time: '2026-07-29T12:01:00Z', temperature_c: -78.2 },
    { event_id: 'new', event_time: '2026-07-29T12:02:00Z' },
  ]);
});
