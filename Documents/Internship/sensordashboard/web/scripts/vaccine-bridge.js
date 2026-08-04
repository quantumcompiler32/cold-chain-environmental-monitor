(function exposeVaccineBridge(global, factory) {
  const api = factory(global);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (global) global.VaccineBridge = api;
})(typeof globalThis === 'undefined' ? this : globalThis, function vaccineBridgeFactory(global) {
  const BRIDGE_URL = 'http://127.0.0.1:8787';

  function buildExportPath(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value != null && String(value) !== '') params.set(key, String(value));
    });
    const query = params.toString();
    return `/api/events/export.csv${query ? `?${query}` : ''}`;
  }

  async function request(path) {
    const response = await global.fetch(`${BRIDGE_URL}${path}`, { cache: 'no-store' });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Dashboard adapter returned ${response.status}`);
    return payload;
  }

  async function exportAllEvents(filters = {}) {
    const response = await global.fetch(`${BRIDGE_URL}${buildExportPath(filters)}`, { cache: 'no-store' });
    if (!response.ok) throw new Error('CSV export is unavailable while PostgreSQL is offline.');
    const blob = await response.blob();
    const link = global.document.createElement('a');
    link.href = global.URL.createObjectURL(blob);
    link.download = 'temperature_events.csv';
    link.click();
    global.URL.revokeObjectURL(link.href);
  }

  function sortEvents(events) {
    return events.slice().sort((left, right) => {
      const timeDifference = Date.parse(left.event_time || left.timestamp || '') - Date.parse(right.event_time || right.timestamp || '');
      return timeDifference || String(left.event_id || '').localeCompare(String(right.event_id || ''));
    });
  }

  function watchEventStream(onEvents, onError, path) {
    const eventSource = new global.EventSource(`${BRIDGE_URL}${path}`);
    const eventsById = new Map();
    let active = true;
    const publish = (payload) => {
      if (!active) return;
      const events = sortEvents(Array.from(eventsById.values()));
      onEvents(events, payload);
    };
    eventSource.addEventListener('snapshot', (message) => {
      const payload = JSON.parse(message.data);
      eventsById.clear();
      (payload.events || []).forEach((event) => eventsById.set(String(event.event_id), event));
      publish(payload);
    });
    eventSource.addEventListener('event', (message) => {
      const payload = JSON.parse(message.data);
      const event = payload.event;
      if (event?.event_id) eventsById.set(String(event.event_id), event);
      publish(payload);
    });
    eventSource.addEventListener('reset', (message) => {
      const payload = JSON.parse(message.data);
      eventsById.clear();
      publish(payload);
    });
    eventSource.onerror = () => {
      if (active) onError(new Error('Live event stream is unavailable.'));
    };
    return () => {
      active = false;
      eventSource.close();
    };
  }

  function watchDatabase(onEvents, onError, path = '/api/live') {
    if (path === '/api/live/stream' && typeof global.EventSource === 'function') {
      return watchEventStream(onEvents, onError, path);
    }
    let active = true;
    const poll = async () => {
      try {
        const payload = await request(path);
        if (active) onEvents(payload.events || [], payload);
      } catch (error) {
        if (active) onError(error);
      }
    };
    poll();
    const timer = setInterval(poll, path === '/api/live' ? 1000 : 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }

  return { request, exportAllEvents, watchDatabase, buildExportPath };
});
