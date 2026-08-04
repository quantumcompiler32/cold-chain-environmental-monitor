(function exposeVaccineBridge(global) {
  const BRIDGE_URL = 'http://127.0.0.1:8787';

  async function request(path) {
    const response = await fetch(`${BRIDGE_URL}${path}`, { cache: 'no-store' });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Dashboard adapter returned ${response.status}`);
    return payload;
  }

  async function exportAllEvents() {
    const response = await fetch(`${BRIDGE_URL}/api/events/export.csv`, { cache: 'no-store' });
    if (!response.ok) throw new Error('CSV export is unavailable while PostgreSQL is offline.');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'temperature_events.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function exportColabTrainingCsv() {
    const response = await fetch(`${BRIDGE_URL}/api/events/export-colab.csv`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Colab CSV export is unavailable while PostgreSQL is offline.');
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'Test1_TempCO2O2.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function sortEvents(events) {
    return events.slice().sort((left, right) => {
      const timeDifference = Date.parse(left.event_time || left.timestamp || '') - Date.parse(right.event_time || right.timestamp || '');
      return timeDifference || String(left.event_id || '').localeCompare(String(right.event_id || ''));
    });
  }

  function watchEventStream(onEvents, onError, path) {
    const eventSource = new EventSource(`${BRIDGE_URL}${path}`);
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

  global.VaccineBridge = { request, exportAllEvents, exportColabTrainingCsv, watchDatabase };
})(typeof globalThis === 'undefined' ? this : globalThis);
