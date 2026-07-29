const assert = require('node:assert/strict');
const test = require('node:test');

const { linearRegression, logisticRegression, kMeans } = require('./phase1-models.js');

function event({ id, pod = 'Pod1', temperature, status, timestamp }) {
  return {
    event_id: id,
    sensor_name: pod,
    temperature_c: temperature,
    status,
    timestamp: timestamp ?? `2026-07-29T${String(10 + id).padStart(2, '0')}:00:00Z`,
    storage_min_c: -80,
    storage_max_c: -60,
    target_c: -78.5,
  };
}

test('linear regression reports a validated near-term temperature trend', () => {
  const events = Array.from({ length: 8 }, (_, index) => event({ id: index + 1, temperature: -78 + index }));

  const result = linearRegression(events);

  assert.equal(result.algorithm, 'linear regression');
  assert.equal(result.status, 'ready');
  assert.equal(result.validation.metric, 'MAE');
  assert.equal(result.slopeCPerHour, 1);
  assert.equal(result.predictedTemperatureC, -70);
});

test('logistic regression estimates out-of-range probability only with both labels', () => {
  const events = [
    ...Array.from({ length: 5 }, (_, index) => event({ id: index + 1, temperature: -78, status: 'STABLE' })),
    ...Array.from({ length: 5 }, (_, index) => event({ id: index + 6, temperature: -55, status: 'TOO_WARM' })),
  ];

  const result = logisticRegression(events);

  assert.equal(result.algorithm, 'logistic regression');
  assert.notEqual(result.status, 'insufficient_data');
  assert.equal(result.validation.metric, 'Accuracy');
  assert.ok(result.excursionProbability > 0.5);
});

test('k-means groups Pods using temperature behavior and exposes its validation score', () => {
  const events = [
    ...[-78.5, -78.4, -78.6].map((temperature, index) => event({ id: index + 1, pod: 'Pod1', temperature, status: 'STABLE' })),
    ...[-70, -69.8, -70.2].map((temperature, index) => event({ id: index + 4, pod: 'Pod2', temperature, status: 'ACCEPTABLE' })),
    ...[-55, -54.5, -55.5].map((temperature, index) => event({ id: index + 7, pod: 'Pod3', temperature, status: 'TOO_WARM' })),
  ];

  const result = kMeans(events);

  assert.equal(result.algorithm, 'k-means clustering');
  assert.equal(result.clusterCount, 3);
  assert.equal(result.clusters.length, 3);
  assert.equal(result.validation.metric, 'Silhouette score');
});

test('each model gives an explicit insufficient-data state', () => {
  const events = [event({ id: 1, temperature: -78, status: 'STABLE' })];

  assert.equal(linearRegression(events).status, 'insufficient_data');
  assert.equal(logisticRegression(events).status, 'insufficient_data');
  assert.equal(kMeans(events).status, 'insufficient_data');
});
