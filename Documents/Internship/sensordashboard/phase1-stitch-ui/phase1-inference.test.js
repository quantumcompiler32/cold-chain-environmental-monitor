const assert = require('node:assert/strict');
const test = require('node:test');

const { buildInferenceEvent, requestPrediction } = require('./phase1-inference.js');

test('builds a small inference event from form values', () => {
  const result = buildInferenceEvent({
    pod: 'Pod2',
    temperature: '-55.25',
    vaccine: 'pfizer_ultralow',
    scenario: 'outlier',
  });

  assert.deepEqual(result, {
    sensor_name: 'Pod2',
    temperature_c: -55.25,
    vaccine_type: 'pfizer_ultralow',
    scenario: 'outlier',
  });
});

test('submits one event and optional context to the inference service', async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ primary: { status: 'ready' } }) };
  };

  const result = await requestPrediction({
    event: { sensor_name: 'Pod1', temperature_c: -78.5 },
    contextEvents: [{ sensor_name: 'Pod2', temperature_c: -78 }],
    fetchImpl,
    baseUrl: 'http://127.0.0.1:5000',
  });

  assert.deepEqual(result, { primary: { status: 'ready' } });
  assert.equal(calls[0].url, 'http://127.0.0.1:5000/api/predict');
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    event: { sensor_name: 'Pod1', temperature_c: -78.5 },
    context_events: [{ sensor_name: 'Pod2', temperature_c: -78 }],
  });
});

test('surfaces service errors to the Interpretation view', async () => {
  const fetchImpl = async () => ({ ok: false, status: 503, json: async () => ({ error: 'Model artifacts are unavailable.' }) });

  await assert.rejects(
    requestPrediction({ event: {}, contextEvents: [], fetchImpl, baseUrl: 'http://127.0.0.1:5000' }),
    /Model artifacts are unavailable/,
  );
});
