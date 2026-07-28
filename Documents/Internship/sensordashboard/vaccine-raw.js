(function initVaccineRaw(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const MAX_VISIBLE_EVENTS = 250;
  let events = [];
  let newestEventKey = null;

  const formatTime = (value) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value || '—') : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };
  const formatTemperature = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(1) + '°C' : '—';
  const statusClass = (status) => String(status || 'UNKNOWN').toLowerCase().replace('_', '-');

  function followNewest() {
    const stream = $('rawStream');
    if (!stream || !$('rawAutoFollow').checked) return;
    global.requestAnimationFrame(() => { stream.scrollTop = 0; });
  }

  function render({ follow = false } = {}) {
    const stream = $('rawStream');
    const previousScrollTop = stream.scrollTop;
    const sensors = [...new Set(events.map((event) => event.sensor_name))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    const scenarios = [...new Set(events.map((event) => event.scenario).filter(Boolean))].sort();
    const sensorFilter = $('rawSensorFilter');
    const scenarioFilter = $('rawScenarioFilter');
    const selectedSensor = sensorFilter.value;
    const selectedScenario = scenarioFilter.value;
    sensorFilter.innerHTML = '<option value="all">ALL PODS</option>' + sensors.map((sensor) => '<option value="' + esc(sensor) + '">' + esc(sensor) + '</option>').join('');
    scenarioFilter.innerHTML = '<option value="all">ALL SCENARIOS</option>' + scenarios.map((scenario) => '<option value="' + esc(scenario) + '">' + esc(scenario.toUpperCase()) + '</option>').join('');
    sensorFilter.value = sensors.includes(selectedSensor) ? selectedSensor : 'all';
    scenarioFilter.value = scenarios.includes(selectedScenario) ? selectedScenario : 'all';
    const matching = events.slice().reverse().filter((event) => (sensorFilter.value === 'all' || event.sensor_name === sensorFilter.value) && (scenarioFilter.value === 'all' || event.scenario === scenarioFilter.value));
    const visible = matching.slice(0, MAX_VISIBLE_EVENTS);
    stream.innerHTML = visible.map((event) => {
      const condition = statusClass(event.status);
      const uncertainty = event.uncertainty_status ? '<span class="raw-uncertainty">' + esc(event.uncertainty_status.replaceAll('_', ' ')) + '</span>' : '';
      return '<article class="raw-row readable-raw-row">'
        + '<div class="raw-event-main"><div><span class="raw-event-time">' + esc(formatTime(event.timestamp)) + '</span><strong>' + esc(event.sensor_name || 'Unknown sensor') + '</strong></div>'
        + '<span class="raw-temperature">' + esc(formatTemperature(event.temperature_c)) + '</span><span class="condition ' + condition + '">' + esc(String(event.status || 'UNKNOWN').replaceAll('_', ' ')) + '</span></div>'
        + '<div class="raw-event-details"><span><b>Profile</b>' + esc(event.vaccine_type || '—') + '</span><span><b>Scenario</b>' + esc(event.scenario || '—') + '</span><span><b>Event ID</b>' + esc(event.event_id || '—') + '</span>' + uncertainty + '</div>'
        + '<details class="raw-payload"><summary>View stored payload</summary><pre>' + esc(JSON.stringify(event, null, 2)) + '</pre></details>'
        + '</article>';
    }).join('') || '<div class="empty">No PostgreSQL events match these filters.</div>';
    $('rowCount').textContent = (matching.length > MAX_VISIBLE_EVENTS ? MAX_VISIBLE_EVENTS + ' of ' : '') + matching.length.toLocaleString();
    $('rawContext').textContent = matching.length > MAX_VISIBLE_EVENTS
      ? 'Rendering the newest ' + MAX_VISIBLE_EVENTS + ' matching events. Expand one row only when you need its raw JSON.'
      : matching.length + ' matching event' + (matching.length === 1 ? '' : 's') + '. Expand one row only when you need its raw JSON.';
    $('statIn').textContent = events.length.toLocaleString();
    $('rawStatusText').textContent = 'PostgreSQL connected · ' + events.length.toLocaleString() + ' persisted events';
    $('rawSource').textContent = 'POSTGRESQL';
    $('rawMode').textContent = 'POSTGRESQL';
    if (follow) followNewest(); else stream.scrollTop = previousScrollTop;
  }

  $('rawSensorFilter').addEventListener('change', render);
  $('rawScenarioFilter').addEventListener('change', render);
  $('rawAutoFollow').addEventListener('change', () => {
    if ($('rawAutoFollow').checked) followNewest();
  });
  $('rawStream').addEventListener('scroll', () => {
    const stream = $('rawStream');
    const atNewest = stream.scrollTop <= 24;
    if (!atNewest && $('rawAutoFollow').checked) $('rawAutoFollow').checked = false;
  });
  bridge.watchDatabase(
    (rawEvents) => {
      events = rawEvents.map((event) => data.normalizeEvent(event));
      const latest = events.at(-1);
      const nextKey = latest ? String(latest.event_id || latest.timestamp || '') : null;
      const receivedNewEvent = newestEventKey !== null && nextKey !== newestEventKey;
      newestEventKey = nextKey;
      render({ follow: $('rawAutoFollow').checked && (receivedNewEvent || events.length > 0) });
    },
    (error) => {
      events = [];
      $('rawStatusText').textContent = 'PostgreSQL unavailable';
      $('rawStream').innerHTML = '<div class="empty">' + esc(error.message) + '</div>';
      $('rawContext').textContent = 'The database bridge is unavailable; no event data is being changed.';
      $('statIn').textContent = '0';
      $('rowCount').textContent = '0';
    }
  );
})(typeof globalThis === 'undefined' ? this : globalThis);
