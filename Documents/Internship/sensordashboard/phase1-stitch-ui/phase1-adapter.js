(function exposePhase1Adapter(root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    let dataModule;
    try { dataModule = require('../vaccine-data.js'); } catch (error) { dataModule = require('../web/scripts/vaccine-data.js'); }
    module.exports = factory(dataModule, require('./phase1-models.js'));
  } else root.Phase1Adapter = factory(root.VaccineData, root.Phase1Models);
})(typeof globalThis === 'undefined' ? this : globalThis, function phase1AdapterFactory(data, models) {
  const POD_NAMES = Array.from({ length: 20 }, (_, index) => `Pod${index + 1}`);
  const SCENARIOS = ['normal', 'outlier', 'failure', 'recovery'];
  const podKey = (value) => String(value || '').replace(/\s+/g, '').toLowerCase();
  const isPodEvent = (event) => /^Pod\s*\d+$/i.test(String(event.sensor_name || ''));
  const timeValue = (value) => { const parsed = Date.parse(String(value || '')); return Number.isFinite(parsed) ? parsed : 0; };
  const sortAscending = (events) => events.slice().sort((left, right) => timeValue(left.timestamp) - timeValue(right.timestamp) || Number(left.event_id) - Number(right.event_id));
  const sortDescending = (events) => sortAscending(events).reverse();

  function normalizeEvents(rawEvents) {
    return (Array.isArray(rawEvents) ? rawEvents : []).map((event) => data.normalizeEvent(event)).filter((event) => isPodEvent(event));
  }

  function filterEvents(events, filters = {}) {
    let result = events.slice();
    if (filters.pod && filters.pod !== 'all') result = result.filter((event) => podKey(event.sensor_name) === podKey(filters.pod));
    if (filters.scenario && filters.scenario !== 'all') result = result.filter((event) => event.scenario === filters.scenario);
    if (filters.timeRange && filters.timeRange !== 'all') {
      const hours = Number(filters.timeRange);
      const latest = Math.max(...result.map((event) => timeValue(event.timestamp)), 0);
      if (Number.isFinite(hours) && latest) result = result.filter((event) => latest - timeValue(event.timestamp) <= hours * 3600000);
    }
    return sortAscending(result);
  }

  function optionsFor(events) {
    return {
      pods: [...new Set(events.map((event) => event.sensor_name))].sort((left, right) => left.localeCompare(right, undefined, { numeric: true })),
      scenarios: [...new Set(events.map((event) => event.scenario).filter(Boolean))].sort(),
    };
  }

  function buildOperationsView(events, filters, acknowledgedIds, connection) {
    const scoped = filterEvents(events, filters);
    const summaries = data.summarizeSensors(scoped);
    const summaryByPod = new Map(summaries.map((summary) => [podKey(summary.sensorName), summary]));
    const packages = POD_NAMES.map((name) => {
      const summary = summaryByPod.get(podKey(name));
      return summary ? { name, temperatureC: summary.latestTemperatureC, status: summary.status, scenario: summary.latestScenario, readings: summary.readingCount, timestamp: summary.latestTimestamp } : { name, temperatureC: null, status: 'UNKNOWN', scenario: null, readings: 0, timestamp: null };
    });
    const attention = summaries.filter((summary) => ['TOO_COLD', 'TOO_WARM'].includes(summary.status) && !acknowledgedIds.has(summary.sensorName)).map((summary) => ({ name: summary.sensorName, temperatureC: summary.latestTemperatureC, status: summary.status, scenario: summary.latestScenario, readings: summary.readingCount, timestamp: summary.latestTimestamp }));
    const inRange = packages.filter((item) => ['STABLE', 'ACCEPTABLE'].includes(item.status)).length;
    const latestEvent = sortDescending(scoped)[0] || null;
    return {
      connection,
      filters: { ...filters },
      packages,
      attention,
      metrics: { activeExcursions: attention.length, podsReporting: summaries.length, expectedPods: 20, readingsInRange: inRange, readingsInRangePercent: summaries.length ? Math.round(inRange / 20 * 100) : null, totalEvents: scoped.length, latestEvent },
      scenarioCounts: data.buildScenarioCounts(scoped),
      borderlineReadings: scoped.filter((event) => String(event.uncertainty_status || '').startsWith('BORDERLINE')).length,
      trendEvents: scoped.slice(-60),
      options: optionsFor(events),
    };
  }

  function buildRawEventsView(events, filters, connection) {
    const matching = filterEvents(events, filters);
    const visible = sortDescending(matching).slice(0, 250);
    return { connection, filters: { ...filters }, events: visible, totalMatching: matching.length, truncated: matching.length > visible.length, options: optionsFor(events) };
  }

  function createPhase1Adapter(rawEvents = [], options = {}) {
    let events = normalizeEvents(rawEvents);
    let connection = options.connection || 'connected';
    const acknowledgedIds = new Set();
    const filters = { pod: 'all', scenario: 'all', timeRange: 'all' };
    return {
      setEvents(nextEvents) { events = normalizeEvents(nextEvents); connection = 'connected'; },
      setOffline() { connection = 'offline'; events = []; },
      setFilters(nextFilters = {}) { Object.assign(filters, nextFilters); },
      acknowledge(pod) { const summary = data.summarizeSensors(filterEvents(events, filters)).find((item) => podKey(item.sensorName) === podKey(pod)); if (summary) acknowledgedIds.add(summary.sensorName); },
      operationsView(overrides = {}) { return buildOperationsView(events, { ...filters, ...overrides }, acknowledgedIds, connection); },
      rawEventsView(overrides = {}) { return buildRawEventsView(events, { ...filters, ...overrides }, connection); },
      analysisView(overrides = {}) { const scoped = filterEvents(events, { ...filters, ...overrides }); return { connection, filters: { ...filters, ...overrides }, events: scoped, options: optionsFor(events) }; },
      runAnalysis(overrides = {}) { const scoped = filterEvents(events, { ...filters, ...overrides }); return scoped.length ? models.runAllModels(scoped) : null; },
      get events() { return events.slice(); },
    };
  }

  return { POD_NAMES, SCENARIOS, normalizeEvents, filterEvents, createPhase1Adapter };
});
