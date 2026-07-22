(function exposeVaccineBridge(global) {
  const BRIDGE_URL = 'http://127.0.0.1:8787';

  async function request(path, options = {}) {
    const response = await fetch(`${BRIDGE_URL}${path}`, { cache: 'no-store', ...options });
    let payload = {};
    try { payload = await response.json(); } catch (error) { /* handled by caller */ }
    if (!response.ok) throw new Error(payload.error || `Bridge request failed (${response.status}).`);
    return payload;
  }

  function createObserver({ onEvent, onStatus, onHealth, onRunStart } = {}) {
    let active = false;
    let eventSource;
    let timer;
    let runId = null;
    let lastSequence = 0;

    function accept(event) {
      if (!active || !runId || event.run_id !== runId) return;
      const sequence = Number(event.event_sequence || event.event_id) || 0;
      if (sequence && sequence <= lastSequence) return;
      lastSequence = Math.max(lastSequence, sequence);
      onEvent?.(event);
    }

    function applyStatus(status) {
      if (status.run_id && status.run_id !== runId) {
        runId = status.run_id;
        lastSequence = 0;
        onRunStart?.(status);
      }
      onStatus?.(status);
    }

    async function poll() {
      if (!active) return;
      try {
        const health = await request('/health');
        onHealth?.(health);
        const status = await request('/api/run/status');
        applyStatus(status);
        if (runId) {
          const events = await request('/api/events');
          events.filter((event) => event.run_id === runId).forEach(accept);
        }
      } catch (error) {
        onHealth?.({ mqtt_connected: false, error: error.message });
      } finally {
        if (active) timer = setTimeout(poll, 500);
      }
    }

    function start() {
      if (active) return;
      active = true;
      if (typeof EventSource !== 'undefined') {
        eventSource = new EventSource(`${BRIDGE_URL}/api/events/stream`);
        eventSource.onmessage = (message) => {
          try {
            const payload = JSON.parse(message.data);
            if (payload.type === 'event') accept(payload.event);
            if (payload.type === 'run_status') applyStatus(payload);
          } catch (error) { /* polling remains the reliable fallback */ }
        };
      }
      poll();
    }

    function stop() {
      active = false;
      clearTimeout(timer);
      eventSource?.close();
      eventSource = null;
    }

    return { start, stop, getRunId: () => runId };
  }

  global.VaccineBridge = { BRIDGE_URL, request, createObserver };
})(typeof globalThis === 'undefined' ? this : globalThis);
