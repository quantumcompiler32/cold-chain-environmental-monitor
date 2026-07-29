(function exposePhase1Models(root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.Phase1Models = factory();
})(typeof globalThis === 'undefined' ? this : globalThis, function phase1ModelsFactory() {
  const sigmoid = (value) => 1 / (1 + Math.exp(-Math.max(-40, Math.min(40, value))));

  function insufficient(algorithm, message, details = {}) {
    return { algorithm, status: 'insufficient_data', message, ...details };
  }

  function linearRegression(events) {
    const points = events
      .map((event) => ({ time: Date.parse(String(event.timestamp)), temperature: Number(event.temperature_c) }))
      .filter((point) => Number.isFinite(point.time) && Number.isFinite(point.temperature))
      .sort((left, right) => left.time - right.time);
    if (points.length < 6) return insufficient('linear regression', 'At least 6 timestamped readings are required.');

    const origin = points[0].time;
    const normalized = points.map((point) => ({ x: (point.time - origin) / 3600000, y: point.temperature }));
    const splitAt = Math.max(4, Math.min(normalized.length - 1, Math.floor(normalized.length * 0.8)));
    const training = normalized.slice(0, splitAt);
    const testing = normalized.slice(splitAt);
    const meanX = training.reduce((sum, point) => sum + point.x, 0) / training.length;
    const meanY = training.reduce((sum, point) => sum + point.y, 0) / training.length;
    const denominator = training.reduce((sum, point) => sum + (point.x - meanX) ** 2, 0);
    const slope = denominator ? training.reduce((sum, point) => sum + (point.x - meanX) * (point.y - meanY), 0) / denominator : 0;
    const intercept = meanY - slope * meanX;
    const predict = (x) => intercept + slope * x;
    const mae = testing.reduce((sum, point) => sum + Math.abs(predict(point.x) - point.y), 0) / testing.length;
    const last = normalized.at(-1);
    const nextX = last.x + Math.max(0.25, last.x - (normalized.at(-2)?.x ?? last.x));
    const predictedTemperatureC = Number(predict(nextX).toFixed(2));
    return {
      algorithm: 'linear regression',
      status: mae <= 2 ? 'ready' : 'low_confidence',
      message: mae <= 2 ? 'Trend estimate available.' : 'Trend estimate has a high validation error.',
      samples: points.length,
      slopeCPerHour: Number(slope.toFixed(4)),
      predictedTemperatureC,
      validation: { metric: 'MAE', value: Number(mae.toFixed(2)), unit: '°C' },
      basis: 'Timestamped temperature readings',
    };
  }

  function logisticRegression(events) {
    const points = events
      .map((event) => {
        const temperature = Number(event.temperature_c);
        const target = Number(event.target_c ?? -78.5);
        const lower = Number(event.storage_min_c ?? -80);
        const upper = Number(event.storage_max_c ?? -60);
        const span = Math.max(Math.abs(upper - lower), 1);
        const label = event.status === 'TOO_COLD' || event.status === 'TOO_WARM' || temperature < lower || temperature > upper ? 1 : 0;
        return { x: (temperature - target) / span, label };
      })
      .filter((point) => Number.isFinite(point.x));
    const labels = new Set(points.map((point) => point.label));
    if (points.length < 8 || labels.size < 2) return insufficient('logistic regression', 'At least 8 readings with both in-range and out-of-range labels are required.');

    const splitAt = Math.max(5, Math.min(points.length - 1, Math.floor(points.length * 0.8)));
    const training = points.slice(0, splitAt);
    const testing = points.slice(splitAt);
    let weight = 0;
    let bias = 0;
    for (let iteration = 0; iteration < 1800; iteration += 1) {
      let weightGradient = 0;
      let biasGradient = 0;
      training.forEach((point) => {
        const error = sigmoid(weight * point.x + bias) - point.label;
        weightGradient += error * point.x;
        biasGradient += error;
      });
      weight -= 0.12 * (weightGradient / training.length + 0.01 * weight);
      bias -= 0.12 * biasGradient / training.length;
    }
    const accuracy = testing.reduce((correct, point) => correct + (Number(sigmoid(weight * point.x + bias) >= 0.5) === point.label ? 1 : 0), 0) / testing.length;
    const latest = points.at(-1);
    const probability = Number(sigmoid(weight * latest.x + bias).toFixed(3));
    return {
      algorithm: 'logistic regression',
      status: accuracy >= 0.6 ? 'ready' : 'low_confidence',
      message: accuracy >= 0.6 ? 'Excursion probability available.' : 'Probability estimate has low validation accuracy.',
      samples: points.length,
      excursionProbability: probability,
      validation: { metric: 'Accuracy', value: Number(accuracy.toFixed(2)), unit: 'ratio' },
      basis: 'Temperature offset from profile target with stored status labels',
    };
  }

  function distance(left, right) {
    return Math.sqrt(left.reduce((sum, value, index) => sum + (value - right[index]) ** 2, 0));
  }

  function kMeans(events) {
    const grouped = new Map();
    events.forEach((event) => {
      const name = String(event.sensor_name || '');
      const temperature = Number(event.temperature_c);
      if (!/^Pod\s*\d+$/i.test(name) || !Number.isFinite(temperature)) return;
      const list = grouped.get(name) || [];
      list.push({ temperature, excursion: event.status === 'TOO_COLD' || event.status === 'TOO_WARM' });
      grouped.set(name, list);
    });
    if (grouped.size < 3) return insufficient('k-means clustering', 'At least 3 Pods with readings are required.');
    const records = Array.from(grouped, ([name, readings]) => {
      const temperatures = readings.map((reading) => reading.temperature);
      return { name, raw: [temperatures.reduce((sum, value) => sum + value, 0) / temperatures.length, Math.max(...temperatures) - Math.min(...temperatures), readings.filter((reading) => reading.excursion).length / readings.length] };
    }).sort((left, right) => left.name.localeCompare(right.name, undefined, { numeric: true }));
    const columns = records[0].raw.map((_, index) => records.map((record) => record.raw[index]));
    const mins = columns.map((values) => Math.min(...values));
    const maxes = columns.map((values) => Math.max(...values));
    records.forEach((record) => { record.features = record.raw.map((value, index) => (value - mins[index]) / Math.max(maxes[index] - mins[index], 1e-9)); });
    const k = Math.min(3, records.length);
    const centers = [records[0].features];
    while (centers.length < k) {
      const next = records.reduce((best, record) => {
        const score = Math.min(...centers.map((center) => distance(record.features, center)));
        return !best || score > best.score ? { score, record } : best;
      }, null).record;
      centers.push(next.features.slice());
    }
    let assignments = [];
    for (let iteration = 0; iteration < 25; iteration += 1) {
      assignments = records.map((record) => centers.reduce((best, center, index) => {
        const score = distance(record.features, center);
        return score < best.score ? { index, score } : best;
      }, { index: 0, score: Infinity }).index);
      const nextCenters = centers.map((_, index) => {
        const members = records.filter((_, recordIndex) => assignments[recordIndex] === index);
        return members.length ? members[0].features.map((_, dimension) => members.reduce((sum, record) => sum + record.features[dimension], 0) / members.length) : centers[index];
      });
      if (nextCenters.every((center, index) => distance(center, centers[index]) < 0.0001)) break;
      nextCenters.forEach((center, index) => { centers[index] = center; });
    }
    const silhouettes = records.map((record, index) => {
      const own = records.filter((_, recordIndex) => assignments[recordIndex] === assignments[index] && recordIndex !== index);
      const other = centers.map((_, clusterIndex) => records.filter((_, recordIndex) => assignments[recordIndex] === clusterIndex && clusterIndex !== assignments[index])).filter((members) => members.length).map((members) => members.reduce((sum, member) => sum + distance(record.features, member.features), 0) / members.length);
      const a = own.length ? own.reduce((sum, member) => sum + distance(record.features, member.features), 0) / own.length : 0;
      const b = other.length ? Math.min(...other) : 0;
      return Math.max(a, b) ? (b - a) / Math.max(a, b) : 0;
    });
    const silhouette = silhouettes.reduce((sum, value) => sum + value, 0) / silhouettes.length;
    return {
      algorithm: 'k-means clustering',
      status: silhouette >= 0.2 ? 'ready' : 'low_confidence',
      message: silhouette >= 0.2 ? 'Pod behavior groups available.' : 'Clusters overlap; use them as exploratory context.',
      samples: events.length,
      clusters: records.map((record, index) => ({ pod: record.name, cluster: assignments[index] + 1, averageTemperatureC: Number(record.raw[0].toFixed(2)), excursionRate: Number(record.raw[2].toFixed(2)) })),
      clusterCount: k,
      validation: { metric: 'Silhouette score', value: Number(silhouette.toFixed(2)), unit: 'ratio' },
      basis: 'Per-Pod average temperature, temperature range, and excursion rate',
    };
  }

  function runAllModels(events) {
    return { linear: linearRegression(events), logistic: logisticRegression(events), clustering: kMeans(events) };
  }

  return { linearRegression, logisticRegression, kMeans, runAllModels };
});
