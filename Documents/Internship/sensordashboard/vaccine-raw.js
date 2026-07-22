(function initVaccineRaw(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  let events = data.createDemoEvents();
  let profile = data.PROFILE;
  let sourceLabel = 'LOCAL';
  let liveMode = false;
  let liveRunId = null;
  let toastTimer;
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));

  function showToast(message) {
    $('toast').textContent = message;
    $('toast').classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2600);
  }

  function render() {
    const sensors = data.summarizeSensors(events).map((sensor) => sensor.sensorName);
    const filter = $('rawSensorFilter');
    const current = filter.value;
    filter.innerHTML = `<option value="all">ALL PODS</option>${sensors.map((sensor) => `<option value="${esc(sensor)}">${esc(sensor)}</option>`).join('')}`;
    filter.value = sensors.includes(current) ? current : 'all';
    const visible = events.slice().sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp) || Number(left.event_id) - Number(right.event_id)).filter((event) => filter.value === 'all' || event.sensor_name === filter.value).slice(-80).reverse();
    $('rawStream').innerHTML = visible.map((event) => {
      const eventText = JSON.stringify(event, null, 2);
      const statusClass = event.status === 'STABLE' || event.status === 'ACCEPTABLE' ? 'val' : 'crit';
      return `<div class="raw-row readable-raw-row"><div class="raw-event-heading"><span class="ts">[${esc(event.timestamp)}]</span><span class="sid">${esc(event.sensor_name)}</span><span class="condition ${statusClass}">${esc(event.status)}</span></div><pre>${esc(eventText)}</pre></div>`;
    }).join('');
    $('rowCount').textContent = visible.length;
    $('statIn').textContent = events.length.toLocaleString();
    $('rawProfile').textContent = profile.label.toUpperCase();
    $('rawSource').textContent = sourceLabel;
    $('rawMode').textContent = liveMode ? 'LIVE' : sourceLabel === 'LOCAL' ? 'LOCAL' : 'FILE';
    $('rawStatusText').textContent = liveMode ? `Live ${profile.label} events` : `${sourceLabel} event data`;
  }

  function applyLiveRun(status) {
    liveMode = true;
    liveRunId = status.run_id;
    events = [];
    profile = data.getProfile(status.profile_id || 'pfizer_ultralow', { min_temp: status.min_temp, max_temp: status.max_temp });
    sourceLabel = 'LIVE';
    render();
  }

  function acceptLiveEvent(event) {
    if (!liveMode || !liveRunId || event.run_id !== liveRunId) return;
    events.push(data.normalizeEvent(event, profile));
    if (events.length > 12000) events = events.slice(-12000);
    render();
  }

  $('rawSensorFilter').addEventListener('change', render);
  $('importButton').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const imported = data.parseTemperatureEvents(String(reader.result), file.name.toLowerCase().endsWith('.json') ? 'json' : 'csv', { maxEvents: 12000, profile });
        if (!imported.length) throw new Error('No temperature events found.');
        liveMode = false;
        liveRunId = null;
        events = data.limitEvents(imported, 12000);
        sourceLabel = file.name;
        render();
        showToast(`Loaded ${events.length.toLocaleString()} events.`);
      } catch (error) { showToast(`Could not load file: ${error.message}`); }
    };
    reader.readAsText(file);
  });
  $('resetButton').addEventListener('click', () => {
    liveMode = false;
    liveRunId = null;
    profile = data.PROFILE;
    events = data.createDemoEvents();
    sourceLabel = 'LOCAL';
    render();
    showToast('Local demo data restored.');
  });

  render();
  const observer = bridge.createObserver({ onHealth: () => {}, onRunStart: applyLiveRun, onEvent: acceptLiveEvent });
  observer.start();
})(typeof globalThis === 'undefined' ? this : globalThis);
