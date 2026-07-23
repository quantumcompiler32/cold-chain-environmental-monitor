(function initVaccineRaw(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  let events = [];

  function render() {
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
    const visible = events.slice().reverse().filter((event) => (sensorFilter.value === 'all' || event.sensor_name === sensorFilter.value) && (scenarioFilter.value === 'all' || event.scenario === scenarioFilter.value));
    $('rawStream').innerHTML = visible.map((event) => {
      const statusClass = event.status === 'STABLE' || event.status === 'ACCEPTABLE' ? 'val' : 'crit';
      return '<div class="raw-row readable-raw-row"><div class="raw-event-heading"><span class="ts">[' + esc(event.timestamp) + ']</span><span class="sid">' + esc(event.sensor_name) + '</span><span class="condition ' + statusClass + '">' + esc(event.status) + '</span></div><pre>' + esc(JSON.stringify(event, null, 2)) + '</pre></div>';
    }).join('') || '<div class="empty">No PostgreSQL events match these filters.</div>';
    $('rowCount').textContent = visible.length.toLocaleString();
    $('statIn').textContent = events.length.toLocaleString();
    $('rawStatusText').textContent = 'PostgreSQL connected · ' + events.length.toLocaleString() + ' persisted events';
    $('rawSource').textContent = 'POSTGRESQL';
    $('rawMode').textContent = 'POSTGRESQL';
  }

  $('rawSensorFilter').addEventListener('change', render);
  $('rawScenarioFilter').addEventListener('change', render);
  bridge.watchDatabase(
    (rawEvents) => {
      events = rawEvents.map((event) => data.normalizeEvent(event));
      render();
    },
    (error) => {
      events = [];
      $('rawStatusText').textContent = 'PostgreSQL unavailable';
      $('rawStream').innerHTML = '<div class="empty">' + esc(error.message) + '</div>';
      $('statIn').textContent = '0';
      $('rowCount').textContent = '0';
    }
  );
})(typeof globalThis === 'undefined' ? this : globalThis);
