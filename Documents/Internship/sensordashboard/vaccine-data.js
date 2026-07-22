(function exposeVaccineData(root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.VaccineData = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function vaccineDataFactory() {
  const PROFILE = Object.freeze({
    id: 'pfizer_ultralow',
    label: 'Pfizer ultralow',
    targetC: -78.5,
    lowerLimitC: -80,
    upperLimitC: -60,
  });

  const STATUS_ORDER = ['STABLE', 'ACCEPTABLE', 'TOO_COLD', 'TOO_WARM'];

  function classifyTemperature(value) {
    const temperature = Number(value);
    if (!Number.isFinite(temperature)) return 'UNKNOWN';
    if (Math.abs(temperature - PROFILE.targetC) <= 1) return 'STABLE';
    if (temperature < PROFILE.lowerLimitC) return 'TOO_COLD';
    if (temperature > PROFILE.upperLimitC) return 'TOO_WARM';
    return 'ACCEPTABLE';
  }

  function parseCsvLine(line) {
    const fields = [];
    let field = '';
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
      const character = line[index];
      const next = line[index + 1];
      if (character === '"' && quoted && next === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = !quoted;
      } else if (character === ',' && !quoted) {
        fields.push(field);
        field = '';
      } else {
        field += character;
      }
    }
    fields.push(field);
    return fields;
  }

  function normalizeEvent(raw) {
    const temperature = Number(raw.temperature_c ?? raw.temperature ?? raw.temp_c);
    return {
      device_id: String(raw.device_id ?? 'vaccine_temperature_simulator'),
      timestamp: String(raw.timestamp ?? raw.event_timestamp ?? raw.received_at ?? ''),
      source_timestamp: String(raw.source_timestamp ?? ''),
      sensor_name: String(raw.sensor_name ?? raw.sensor ?? 'Unknown'),
      vaccine_type: String(raw.vaccine_type ?? PROFILE.id),
      scenario: String(raw.scenario ?? 'normal'),
      temperature_c: temperature,
      status: classifyTemperature(temperature),
    };
  }

  function parseTemperatureEvents(input, format) {
    if (Array.isArray(input)) return input.map(normalizeEvent).filter((event) => Number.isFinite(event.temperature_c));
    if (typeof input !== 'string' || !input.trim()) return [];

    if (format === 'json' || input.trim().startsWith('[') || input.trim().startsWith('{')) {
      const parsed = JSON.parse(input);
      const events = Array.isArray(parsed) ? parsed : (parsed.events || parsed.data || [parsed]);
      return events.map(normalizeEvent).filter((event) => Number.isFinite(event.temperature_c));
    }

    const lines = input.trim().split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) return [];
    const headers = parseCsvLine(lines[0]).map((header) => header.trim());
    return lines.slice(1).map((line) => {
      const values = parseCsvLine(line);
      return normalizeEvent(Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ''])));
    }).filter((event) => Number.isFinite(event.temperature_c));
  }

  function timestampValue(timestamp) {
    const value = Date.parse(String(timestamp).replace(' ', 'T'));
    return Number.isFinite(value) ? value : 0;
  }

  function sortedEvents(events) {
    return events.slice().sort((left, right) => timestampValue(left.timestamp) - timestampValue(right.timestamp));
  }

  function summarizeSensors(events) {
    const groups = new Map();
    sortedEvents(events).forEach((event) => {
      if (!groups.has(event.sensor_name)) groups.set(event.sensor_name, []);
      groups.get(event.sensor_name).push(event);
    });

    return Array.from(groups.entries()).sort(([left], [right]) => left.localeCompare(right, undefined, { numeric: true })).map(([sensorName, sensorEvents]) => {
      const temperatures = sensorEvents.map((event) => event.temperature_c);
      const latest = sensorEvents[sensorEvents.length - 1];
      const statusCounts = STATUS_ORDER.reduce((counts, status) => {
        counts[status] = sensorEvents.filter((event) => event.status === status).length;
        return counts;
      }, {});
      return {
        sensorName,
        latestTemperatureC: latest.temperature_c,
        latestTimestamp: latest.timestamp,
        latestScenario: latest.scenario,
        status: latest.status,
        averageTemperatureC: temperatures.reduce((sum, value) => sum + value, 0) / temperatures.length,
        minimumTemperatureC: Math.min(...temperatures),
        maximumTemperatureC: Math.max(...temperatures),
        readingCount: sensorEvents.length,
        excursionCount: statusCounts.TOO_COLD + statusCounts.TOO_WARM,
        statusCounts,
      };
    });
  }

  function buildChartSeries(events, selectedSensors) {
    const sensors = selectedSensors && selectedSensors.length
      ? selectedSensors
      : summarizeSensors(events).slice(0, 6).map((sensor) => sensor.sensorName);
    const bySensor = new Map(sensors.map((sensor) => [sensor, new Map()]));
    sortedEvents(events).forEach((event) => {
      if (bySensor.has(event.sensor_name)) bySensor.get(event.sensor_name).set(event.timestamp, event.temperature_c);
    });
    const labels = Array.from(new Set(sortedEvents(events).map((event) => event.timestamp)));
    return {
      labels,
      series: sensors.map((sensorName) => ({
        sensorName,
        values: labels.map((label) => bySensor.get(sensorName).get(label) ?? null),
      })),
    };
  }

  function buildStatusCounts(events) {
    return STATUS_ORDER.reduce((counts, status) => {
      counts[status] = events.filter((event) => event.status === status).length;
      return counts;
    }, {});
  }

  function buildScenarioCounts(events) {
    return events.reduce((counts, event) => {
      counts[event.scenario] = (counts[event.scenario] || 0) + 1;
      return counts;
    }, {});
  }

  function buildExcursionSeries(events) {
    const buckets = new Map();
    sortedEvents(events).forEach((event) => {
      const day = String(event.timestamp).slice(0, 10) || 'Unknown';
      const bucket = buckets.get(day) || { tooCold: 0, tooWarm: 0 };
      if (event.status === 'TOO_COLD') bucket.tooCold += 1;
      if (event.status === 'TOO_WARM') bucket.tooWarm += 1;
      buckets.set(day, bucket);
    });
    return Array.from(buckets.entries()).map(([label, value]) => ({ label, ...value }));
  }

  function buildReplayOffsetSeries(events) {
    return sortedEvents(events).slice(-30).map((event) => {
      const eventTime = timestampValue(event.timestamp);
      const sourceTime = timestampValue(event.source_timestamp);
      return { label: event.timestamp, hours: sourceTime && eventTime ? (eventTime - sourceTime) / 3600000 : null };
    });
  }

  function createDemoEvents() {
    const sensors = Array.from({ length: 20 }, (_, index) => `Pod${index + 1}`);
    const scenarios = ['normal', 'normal', 'normal', 'recovery', 'outlier', 'failure'];
    const events = [];
    sensors.forEach((sensorName, sensorIndex) => {
      for (let point = 0; point < 24; point += 1) {
        const base = PROFILE.targetC + Math.sin((point + sensorIndex) / 3) * 0.7 + ((sensorIndex % 5) - 2) * 0.18;
        const isColdExcursion = sensorIndex === 2 && point >= 16 && point <= 18;
        const isWarmExcursion = sensorIndex === 10 && point >= 19 && point <= 21;
        const temperature = isColdExcursion ? -82 + (point - 16) * 0.5 : isWarmExcursion ? -59.2 - (point - 20) * 0.25 : base;
        const sourceTimestamp = new Date(Date.UTC(2020, 11, 16, 11, 25, 54 + point * 10 + sensorIndex));
        const timestamp = new Date(Date.UTC(2026, 6, 21, 8 + point, 0, 0));
        events.push(normalizeEvent({
          device_id: 'vaccine_temperature_simulator',
          timestamp: timestamp.toISOString(),
          source_timestamp: sourceTimestamp.toISOString(),
          sensor_name: sensorName,
          vaccine_type: PROFILE.id,
          scenario: scenarios[(point + sensorIndex) % scenarios.length],
          temperature_c: Number(temperature.toFixed(2)),
        }));
      }
    });
    return events;
  }

  function toCsv(events) {
    const headers = ['device_id', 'timestamp', 'source_timestamp', 'sensor_name', 'vaccine_type', 'scenario', 'temperature_c', 'status'];
    const quote = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;
    return [headers.join(','), ...events.map((event) => headers.map((header) => quote(event[header])).join(','))].join('\n');
  }

  return {
    PROFILE,
    STATUS_ORDER,
    classifyTemperature,
    parseTemperatureEvents,
    summarizeSensors,
    buildChartSeries,
    buildStatusCounts,
    buildScenarioCounts,
    buildExcursionSeries,
    buildReplayOffsetSeries,
    createDemoEvents,
    toCsv,
  };
});
