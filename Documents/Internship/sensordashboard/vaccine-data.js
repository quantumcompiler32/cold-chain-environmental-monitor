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

  const SENSOR_TOLERANCE_C = 0.5;

  const STATUS_ORDER = ['STABLE', 'ACCEPTABLE', 'TOO_COLD', 'TOO_WARM'];
  const PROFILE_DEFINITIONS = {
    pfizer_ultralow: { id: 'pfizer_ultralow', label: 'Pfizer ultralow', targetC: -78.5, lowerLimitC: -80, upperLimitC: -60, guidance: 'Simulation profile based on the Pfizer ultralow cold-chain range.', sourceUrl: '' },
    moderna: { id: 'moderna', label: 'Moderna / Spikevax', targetC: -32.5, lowerLimitC: -50, upperLimitC: -15, guidance: 'Suggested frozen-storage bounds from Moderna Spikevax guidance; editable for your simulation.', sourceUrl: 'https://products.modernatx.com/spikevaxpro/dosing-and-administration' },
  };

  function getProfile(id = PROFILE.id, bounds = {}) {
    const base = PROFILE_DEFINITIONS[id] || PROFILE_DEFINITIONS[PROFILE.id];
    const lowerLimitC = bounds.min_temp == null ? base.lowerLimitC : Number(bounds.min_temp);
    const upperLimitC = bounds.max_temp == null ? base.upperLimitC : Number(bounds.max_temp);
    return Object.freeze({ ...base, lowerLimitC, upperLimitC });
  }

  function classifyTemperature(value, profile = PROFILE) {
    const temperature = Number(value);
    if (!Number.isFinite(temperature)) return 'UNKNOWN';
    if (!Number.isFinite(profile.lowerLimitC) || !Number.isFinite(profile.upperLimitC)) return 'UNKNOWN';
    if (temperature < profile.lowerLimitC) return 'TOO_COLD';
    if (temperature > profile.upperLimitC) return 'TOO_WARM';
    if (Math.abs(temperature - profile.targetC) <= 1) return 'STABLE';
    return 'ACCEPTABLE';
  }

  function classifyUncertainty(value, profile = PROFILE, tolerance = SENSOR_TOLERANCE_C) {
    const temperature = Number(value);
    const lower = Number(profile.lowerLimitC);
    const upper = Number(profile.upperLimitC);
    const margin = Number(tolerance);
    if (![temperature, lower, upper, margin].every(Number.isFinite)) return 'UNKNOWN';
    const possibleMin = temperature - margin;
    const possibleMax = temperature + margin;
    const crossesLower = possibleMin < lower && possibleMax >= lower;
    const crossesUpper = possibleMin <= upper && possibleMax > upper;
    if (crossesLower && crossesUpper) return 'BORDERLINE_RANGE';
    if (crossesLower) return 'BORDERLINE_COLD';
    if (crossesUpper) return 'BORDERLINE_WARM';
    if (possibleMax < lower) return 'CLEARLY_TOO_COLD';
    if (possibleMin > upper) return 'CLEARLY_TOO_WARM';
    return 'WITHIN_RANGE';
  }

  function uncertaintyFields(value, profile = PROFILE, tolerance = SENSOR_TOLERANCE_C) {
    const temperature = Number(value);
    const margin = Number(tolerance);
    const possibleMin = Number((temperature - margin).toFixed(2));
    const possibleMax = Number((temperature + margin).toFixed(2));
    return {
      sensor_tolerance_c: Number(margin.toFixed(2)),
      temperature_min_possible_c: possibleMin,
      temperature_max_possible_c: possibleMax,
      storage_min_c: Number(profile.lowerLimitC),
      storage_max_c: Number(profile.upperLimitC),
      uncertainty_status: classifyUncertainty(temperature, profile, margin),
      boundary_crossing: classifyUncertainty(temperature, profile, margin).startsWith('BORDERLINE'),
      measurement_confidence: 'Approximately +/-0.5 C Type-T thermocouple accuracy',
    };
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

  function normalizeEvent(raw, profile = PROFILE) {
    const temperature = Number(raw.temperature_c ?? raw.temperature ?? raw.temp_c);
    return {
      event_id: String(raw.event_id ?? raw.event_sequence ?? raw.received_at ?? `${raw.timestamp ?? raw.event_timestamp ?? ''}|${raw.sensor_name ?? raw.sensor ?? ''}|${temperature}`),
      device_id: String(raw.device_id ?? 'vaccine_temperature_simulator'),
      timestamp: String(raw.timestamp ?? raw.event_timestamp ?? raw.received_at ?? ''),
      received_at: String(raw.received_at ?? ''),
      source_timestamp: String(raw.source_timestamp ?? ''),
      sensor_name: String(raw.sensor_name ?? raw.sensor ?? 'Unknown'),
      vaccine_type: String(raw.vaccine_type ?? PROFILE.id),
      scenario: String(raw.scenario ?? 'normal'),
      temperature_c: temperature,
      status: classifyTemperature(temperature, profile),
      ...uncertaintyFields(temperature, profile, raw.sensor_tolerance_c ?? SENSOR_TOLERANCE_C),
    };
  }

  function parseDateTime(dateText, timeText) {
    const dateParts = String(dateText).trim().match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2,4})$/);
    const timeParts = String(timeText).trim().match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?/);
    if (dateParts && timeParts) {
      const months = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
      const year = dateParts[3].length === 2 ? 2000 + Number(dateParts[3]) : Number(dateParts[3]);
      const month = months[dateParts[2][0].toUpperCase() + dateParts[2].slice(1).toLowerCase()];
      if (month !== undefined) return new Date(Date.UTC(year, month, Number(dateParts[1]), Number(timeParts[1]), Number(timeParts[2]), Number(timeParts[3] || 0))).toISOString();
    }
    const parsed = Date.parse(`${dateText} ${timeText} UTC`);
    return Number.isFinite(parsed) ? new Date(parsed).toISOString() : '';
  }

  function parseWideTemperatureCsv(lines, headers, options = {}) {
    const profile = options.profile || PROFILE;
    const dateIndex = headers.findIndex((header) => header.toLowerCase() === 'date');
    const timeIndex = headers.findIndex((header) => header.toLowerCase() === 'time');
    const podColumns = headers.map((header, index) => ({ header, index })).filter(({ header }) => /^pod\d+$/i.test(header));
    const dataLines = lines.slice(1);
    const maxEvents = Number.isFinite(options.maxEvents) ? options.maxEvents : Infinity;
    const maxRows = Number.isFinite(maxEvents) ? Math.max(1, Math.floor(maxEvents / Math.max(podColumns.length, 1))) : dataLines.length;
    const rowStride = Math.max(1, Math.ceil(dataLines.length / maxRows));
    const events = [];
    dataLines.forEach((line, rowIndex) => {
      if (rowIndex % rowStride !== 0 || events.length >= maxEvents) return;
      const values = parseCsvLine(line);
      const timestamp = parseDateTime(values[dateIndex], values[timeIndex]);
      if (!timestamp) return;
      podColumns.forEach(({ header, index }) => {
        const fahrenheit = Number(values[index]);
        if (!Number.isFinite(fahrenheit)) return;
        events.push(normalizeEvent({
          device_id: 'vaccine_temperature_dataset',
          timestamp,
          source_timestamp: timestamp,
          sensor_name: header,
          vaccine_type: PROFILE.id,
          scenario: 'normal',
          temperature_c: Number(((fahrenheit - 32) * 5 / 9).toFixed(2)),
        }, profile));
      });
    });
    return events;
  }

  function limitEvents(events, maxEvents = 12000) {
    if (!Number.isFinite(maxEvents) || events.length <= maxEvents) return events;
    const bySensor = new Map();
    events.forEach((event) => {
      if (!bySensor.has(event.sensor_name)) bySensor.set(event.sensor_name, []);
      bySensor.get(event.sensor_name).push(event);
    });
    const perSensor = Math.max(1, Math.floor(maxEvents / bySensor.size));
    return Array.from(bySensor.values()).flatMap((sensorEvents) => {
      const stride = Math.max(1, Math.ceil(sensorEvents.length / perSensor));
      return sensorEvents.filter((_, index) => index % stride === 0).slice(0, perSensor);
    });
  }

  function getChartHeight(sensorCount) {
    return 340;
  }

  function parseTemperatureEvents(input, format, options = {}) {
    const profile = options.profile || PROFILE;
    if (Array.isArray(input)) return limitEvents(input.map((event) => normalizeEvent(event, profile)).filter((event) => Number.isFinite(event.temperature_c)), options.maxEvents);
    if (typeof input !== 'string' || !input.trim()) return [];

    if (format === 'json' || input.trim().startsWith('[') || input.trim().startsWith('{')) {
      const parsed = JSON.parse(input);
      const events = Array.isArray(parsed) ? parsed : (parsed.events || parsed.data || [parsed]);
      return limitEvents(events.map((event) => normalizeEvent(event, profile)).filter((event) => Number.isFinite(event.temperature_c)), options.maxEvents);
    }

    const lines = input.trim().split(/\r?\n/).filter(Boolean);
    if (lines.length < 2) return [];
    const headers = parseCsvLine(lines[0]).map((header) => header.trim());
    if (headers.some((header) => header.toLowerCase() === 'date') && headers.some((header) => header.toLowerCase() === 'time') && headers.some((header) => /^pod\d+$/i.test(header))) {
      return parseWideTemperatureCsv(lines, headers, options);
    }
    return lines.slice(1).map((line) => {
      const values = parseCsvLine(line);
      return normalizeEvent(Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ''])), profile);
    }).filter((event) => Number.isFinite(event.temperature_c)).slice(0, options.maxEvents || undefined);
  }

  function timestampValue(timestamp) {
    const value = Date.parse(String(timestamp).replace(' ', 'T'));
    return Number.isFinite(value) ? value : 0;
  }

  function eventSequence(event) {
    const value = Number(event.event_id);
    return Number.isFinite(value) ? value : 0;
  }

  function sortedEvents(events) {
    return events.slice().sort((left, right) => timestampValue(left.timestamp) - timestampValue(right.timestamp) || eventSequence(left) - eventSequence(right));
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
    const byTimestamp = new Map();
    sortedEvents(events).forEach((event) => {
      if (!sensors.includes(event.sensor_name)) return;
      const bucket = byTimestamp.get(event.timestamp) || new Map();
      const values = bucket.get(event.sensor_name) || [];
      values.push(event.temperature_c);
      bucket.set(event.sensor_name, values);
      byTimestamp.set(event.timestamp, bucket);
    });
    const labels = [];
    Array.from(byTimestamp.entries()).forEach(([timestamp, bucket]) => {
      const occurrences = Math.max(...sensors.map((sensor) => (bucket.get(sensor) || []).length), 1);
      for (let occurrence = 0; occurrence < occurrences; occurrence += 1) labels.push({ timestamp, occurrence });
    });
    return {
      labels: labels.map((point) => point.timestamp),
      series: sensors.map((sensorName) => ({
        sensorName,
        values: labels.map((label, index) => {
          const point = labels[index];
          const bucket = byTimestamp.get(point.timestamp);
          const values = bucket?.get(sensorName) || [];
          const prior = labels.slice(0, index).filter((candidate) => candidate.timestamp === point.timestamp).length;
          return values[prior] ?? null;
        }),
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

  function buildScenarioOutcomeSeries(events) {
    const groups = new Map();
    events.forEach((event) => {
      const group = groups.get(event.scenario) || { label: event.scenario, total: 0, tooCold: 0, tooWarm: 0, borderline: 0, crossing: 0 };
      group.total += 1;
      if (event.status === 'TOO_COLD') group.tooCold += 1;
      if (event.status === 'TOO_WARM') group.tooWarm += 1;
      if (String(event.uncertainty_status || '').startsWith('BORDERLINE')) group.borderline += 1;
      if (event.boundary_crossing) group.crossing += 1;
      groups.set(event.scenario, group);
    });
    return Array.from(groups.values());
  }

  function buildSensorSpreadSeries(events, selectedSensors = []) {
    const selected = selectedSensors.length ? selectedSensors : summarizeSensors(events).map((sensor) => sensor.sensorName);
    return selected.map((sensorName) => {
      const values = events.filter((event) => event.sensor_name === sensorName).map((event) => event.temperature_c).filter(Number.isFinite);
      if (!values.length) return { label: sensorName, minimum: null, average: null, maximum: null };
      return { label: sensorName, minimum: Math.min(...values), average: values.reduce((sum, value) => sum + value, 0) / values.length, maximum: Math.max(...values) };
    }).filter((value) => value.minimum !== null);
  }

  function buildUncertaintySeries(events) {
    const groups = new Map();
    events.forEach((event) => {
      const day = String(event.timestamp).slice(0, 10) || 'Unknown';
      const group = groups.get(day) || { label: day, borderline: 0, crossing: 0 };
      if (String(event.uncertainty_status || '').startsWith('BORDERLINE')) group.borderline += 1;
      if (event.boundary_crossing) group.crossing += 1;
      groups.set(day, group);
    });
    return Array.from(groups.values());
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
        const isColdExcursion = sensorIndex === 2 && point >= 20 && point <= 23;
        const isWarmExcursion = sensorIndex === 10 && point >= 20 && point <= 23;
        const temperature = isColdExcursion ? -82 + (point - 20) * 0.5 : isWarmExcursion ? -59.2 - (point - 20) * 0.25 : base;
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
    const headers = ['device_id', 'timestamp', 'source_timestamp', 'sensor_name', 'vaccine_type', 'scenario', 'temperature_c', 'status', 'sensor_tolerance_c', 'temperature_min_possible_c', 'temperature_max_possible_c', 'storage_min_c', 'storage_max_c', 'uncertainty_status', 'boundary_crossing', 'measurement_confidence'];
    const quote = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`;
    return [headers.join(','), ...events.map((event) => headers.map((header) => quote(event[header])).join(','))].join('\n');
  }

  return {
    PROFILE,
    SENSOR_TOLERANCE_C,
    PROFILE_DEFINITIONS,
    getProfile,
    normalizeEvent,
    STATUS_ORDER,
    classifyTemperature,
    classifyUncertainty,
    uncertaintyFields,
    parseTemperatureEvents,
    summarizeSensors,
    buildChartSeries,
    buildStatusCounts,
    buildScenarioCounts,
    buildScenarioOutcomeSeries,
    buildSensorSpreadSeries,
    buildUncertaintySeries,
    buildExcursionSeries,
    buildReplayOffsetSeries,
    createDemoEvents,
    limitEvents,
    getChartHeight,
    toCsv,
  };
});
