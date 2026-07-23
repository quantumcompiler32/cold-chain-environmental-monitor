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

  function watchDatabase(onEvents, onError) {
    let active = true;
    const poll = async () => {
      try {
        const payload = await request('/api/events');
        if (active) onEvents(payload.events || []);
      } catch (error) {
        if (active) onError(error);
      }
    };
    poll();
    const timer = setInterval(poll, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }

  global.VaccineBridge = { request, exportAllEvents, watchDatabase };
})(typeof globalThis === 'undefined' ? this : globalThis);
