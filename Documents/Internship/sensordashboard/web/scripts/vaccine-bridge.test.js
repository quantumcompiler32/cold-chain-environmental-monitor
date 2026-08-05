/* Purpose: test the bridge's URL construction and read-only client behavior. */
const assert = require('node:assert/strict');
const test = require('node:test');

const { buildExportPath } = require('./vaccine-bridge.js');

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
