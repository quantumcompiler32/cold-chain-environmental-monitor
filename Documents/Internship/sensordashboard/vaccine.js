(function initVaccineAnalytics(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data) return;

  const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#6b7280'];
  const SCENARIO_COLORS = { normal: '#10b981', recovery: '#3b82f6', outlier: '#f59e0b', failure: '#ef4444' };
  const DEFAULT_SENSORS = ['Pod1', 'Pod2', 'Pod3', 'Pod6', 'Pod11', 'Pod20'];
  let events = data.createDemoEvents();
  let selectedSensors = DEFAULT_SENSORS.slice();
  let profile = data.PROFILE;
  let dataLabel = 'Using built-in demo events';
  let sourceLabel = 'LOCAL';
  let liveMode = false;
  let liveRunId = null;
  let runSensors = null;
  let renderQueued = false;
  let toastTimer;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const formatC = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}°C` : '—';
  const statusLabel = (status) => ({ STABLE: 'Stable', ACCEPTABLE: 'Acceptable', TOO_COLD: 'Too cold', TOO_WARM: 'Too warm', UNKNOWN: 'No reading' }[status] || status);
  const statusClass = (status) => String(status || 'UNKNOWN').toLowerCase().replace('_', '-');
  const sorted = (list) => list.slice().sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp) || Number(left.event_id) - Number(right.event_id));
  const rangeText = () => `${formatC(profile.lowerLimitC)} to ${formatC(profile.upperLimitC)}`;

  function showToast(message) {
    const toast = $('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
  }

  function setBridgeState(online, message) {
    const status = $('bridgeStatus');
    if (!status) return;
    status.classList.toggle('online', online);
    status.classList.toggle('offline', !online);
    status.innerHTML = `<i></i>${esc(message || (online ? 'Live bridge connected' : 'Live bridge offline'))}`;
  }

  function applyProfile(profileId, bounds = {}) {
    profile = data.getProfile(profileId, bounds);
    $('profileGuidance').textContent = profile.guidance || 'Statuses are derived from each reading.';
    $('profileSourceLink').href = profile.sourceUrl || '#';
    $('profileSourceLink').style.display = profile.sourceUrl ? 'inline' : 'none';
  }

  function renderKpis(summaries) {
    const inRange = summaries.filter((sensor) => sensor.status === 'STABLE' || sensor.status === 'ACCEPTABLE').length;
    const warmest = summaries.reduce((best, sensor) => !best || sensor.latestTemperatureC > best.latestTemperatureC ? sensor : best, null);
    const coldest = summaries.reduce((best, sensor) => !best || sensor.latestTemperatureC < best.latestTemperatureC ? sensor : best, null);
    const latestEvent = sorted(events).at(-1);
    $('kpiInRange').textContent = `${inRange}/${summaries.length}`;
    $('kpiInRangeDetail').textContent = inRange === summaries.length ? 'All package sensors acceptable' : `${summaries.length - inRange} sensor${summaries.length - inRange === 1 ? '' : 's'} outside range`;
    $('kpiWarmest').textContent = formatC(warmest?.latestTemperatureC);
    $('kpiWarmestDetail').textContent = warmest ? `${warmest.sensorName} · ${statusLabel(warmest.status)}` : 'No readings';
    $('kpiColdest').textContent = formatC(coldest?.latestTemperatureC);
    $('kpiColdestDetail').textContent = coldest ? `${coldest.sensorName} · ${statusLabel(coldest.status)}` : 'No readings';
    $('kpiEvents').textContent = events.length.toLocaleString();
    $('kpiEventsDetail').textContent = latestEvent ? `Latest event ${new Date(latestEvent.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'No readings';
  }

  function renderAttention(summaries) {
    const attention = $('attentionBanner');
    const outOfRange = summaries.filter((sensor) => sensor.status === 'TOO_COLD' || sensor.status === 'TOO_WARM');
    const names = outOfRange.slice(0, 3).map((sensor) => sensor.sensorName).join(', ');
    attention.classList.toggle('safe', outOfRange.length === 0);
    $('attentionTitle').textContent = outOfRange.length ? `Simulation: ${outOfRange.length} sensor${outOfRange.length === 1 ? '' : 's'} outside range` : 'All simulated sensors are in range';
    $('attentionText').textContent = outOfRange.length ? `${names}${outOfRange.length > 3 ? ' and more' : ''} are outside ${rangeText()}. Use the visualizations to inspect the generated behavior.` : `The latest simulated readings are within the ${profile.label} range.`;
  }

  function renderPicker(availableSensors) {
    const picker = $('sensorPicker');
    const active = selectedSensors.filter((sensor) => availableSensors.includes(sensor));
    if (!liveMode) selectedSensors = active.length ? active : availableSensors.length ? availableSensors.slice(0, 6) : selectedSensors;
    picker.innerHTML = availableSensors.map((sensorName, index) => `<button class="sensor-chip${selectedSensors.includes(sensorName) ? ' selected' : ''}" type="button" aria-pressed="${selectedSensors.includes(sensorName)}" data-sensor="${esc(sensorName)}" style="--chip-color:${COLORS[index % COLORS.length]}"${liveMode ? ' disabled title="Selected in the live run"' : ''}>${esc(sensorName)}</button>`).join('');
    if (liveMode) return;
    picker.querySelectorAll('[data-sensor]').forEach((button) => button.addEventListener('click', () => {
      const sensor = button.dataset.sensor;
      selectedSensors = selectedSensors.includes(sensor) ? selectedSensors.filter((item) => item !== sensor) : [...selectedSensors, sensor];
      if (!selectedSensors.length) selectedSensors = [sensor];
      render();
    }));
  }

  function linePath(values, x, y) {
    let path = '';
    let hasPrevious = false;
    values.forEach((value, index) => {
      if (value === null || value === undefined) { hasPrevious = false; return; }
      path += `${hasPrevious ? 'L' : 'M'}${x(index).toFixed(1)},${y(value).toFixed(1)} `;
      hasPrevious = true;
    });
    return path.trim();
  }

  function renderTemperatureChart() {
    const target = $('temperatureChart');
    const chart = data.buildChartSeries(events, selectedSensors);
    const width = Math.max(target.clientWidth || 620, 320);
    const height = 340;
    target.style.height = `${height}px`;
    const margin = { top: 14, right: 12, bottom: 28, left: 40 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const lower = profile.lowerLimitC;
    const upper = profile.upperLimitC;
    const min = Math.min(lower, profile.targetC) - 5;
    const max = Math.max(upper, profile.targetC) + 5;
    const x = (index) => margin.left + (chart.labels.length <= 1 ? plotWidth / 2 : index * plotWidth / (chart.labels.length - 1));
    const y = (value) => margin.top + (max - value) * plotHeight / (max - min);
    const yTicks = Array.from({ length: 7 }, (_, index) => min + (max - min) * index / 6).reverse();
    const xTicks = chart.labels.map((label, index) => ({ label, index })).filter((_, index) => index === 0 || index === chart.labels.length - 1 || index % Math.max(1, Math.floor(chart.labels.length / 5)) === 0);
    const grid = yTicks.map((tick) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(tick)}" y2="${y(tick)}" stroke="rgba(255,255,255,.06)"/><text x="${margin.left - 8}" y="${y(tick) + 3}" text-anchor="end" fill="#6b7280" font-size="10">${tick.toFixed(1)}°</text>`).join('');
    const labels = xTicks.map(({ label, index }) => `<text x="${x(index)}" y="${height - 7}" text-anchor="middle" fill="#6b7280" font-size="10">${esc(new Date(label).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))}</text>`).join('');
    const lines = chart.series.map((series, index) => `<path d="${linePath(series.values, x, y)}" fill="none" stroke="${COLORS[index % COLORS.length]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`).join('');
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Selected package temperature trend"><rect x="${margin.left}" y="${y(upper)}" width="${plotWidth}" height="${y(lower) - y(upper)}" fill="rgba(16,185,129,.1)"/><line x1="${margin.left}" x2="${width - margin.right}" y1="${y(lower)}" y2="${y(lower)}" stroke="rgba(96,165,250,.65)" stroke-dasharray="4 4"/><line x1="${margin.left}" x2="${width - margin.right}" y1="${y(upper)}" y2="${y(upper)}" stroke="rgba(239,68,68,.65)" stroke-dasharray="4 4"/><line x1="${margin.left}" x2="${width - margin.right}" y1="${y(profile.targetC)}" y2="${y(profile.targetC)}" stroke="#fbbf24" stroke-dasharray="2 4"/>${grid}${lines}${labels}</svg>`;
  }

  function renderStatusBars(summaries) {
    const counts = summaries.reduce((result, sensor) => { result[sensor.status] = (result[sensor.status] || 0) + 1; return result; }, {});
    const total = Math.max(summaries.length, 1);
    const colors = { STABLE: '#10b981', ACCEPTABLE: '#34d399', TOO_COLD: '#60a5fa', TOO_WARM: '#ef4444', UNKNOWN: '#6b7280' };
    $('healthSummary').innerHTML = `<strong>${summaries.filter((sensor) => sensor.status === 'STABLE' || sensor.status === 'ACCEPTABLE').length}/${summaries.length}</strong><span>package sensors in range</span>`;
    $('statusBars').innerHTML = data.STATUS_ORDER.concat(Object.keys(counts).filter((key) => !data.STATUS_ORDER.includes(key))).map((status) => `<div class="status-bar-row"><label>${statusLabel(status)}</label><div class="status-bar-track"><div class="status-bar-fill" style="width:${((counts[status] || 0) / total) * 100}%;background:${colors[status] || '#6b7280'}"></div></div><span class="status-count">${counts[status] || 0}</span></div>`).join('');
  }

  function renderBars(target, values, colors, formatter) {
    const width = Math.max(target.clientWidth || 420, 280);
    const height = 170;
    const margin = { top: 12, right: 12, bottom: 30, left: 28 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const max = Math.max(...values.map((value) => value.total || value.count || value.tooCold + value.tooWarm || 0), 1);
    const barWidth = Math.max(10, plotWidth / Math.max(values.length * 1.55, 1));
    const barGap = (plotWidth - barWidth * values.length) / Math.max(values.length, 1);
    const bars = values.map((value, index) => {
      const total = value.total || value.count || value.tooCold + value.tooWarm || 0;
      const barX = margin.left + index * (barWidth + barGap);
      const barY = margin.top + plotHeight - total / max * plotHeight;
      if (value.tooCold !== undefined) {
        const coldHeight = value.tooCold / max * plotHeight;
        const warmHeight = value.tooWarm / max * plotHeight;
        return `<rect x="${barX}" y="${barY + warmHeight}" width="${barWidth}" height="${coldHeight}" fill="${colors.cold}" rx="3"/><rect x="${barX}" y="${barY}" width="${barWidth}" height="${warmHeight}" fill="${colors.warm}" rx="3"/><text x="${barX + barWidth / 2}" y="${height - 8}" text-anchor="middle" fill="#6b7280" font-size="9">${esc(value.label.slice(5))}</text>`;
      }
      return `<rect x="${barX}" y="${barY}" width="${barWidth}" height="${total / max * plotHeight}" fill="${colors[index % colors.length]}" rx="3"/><text x="${barX + barWidth / 2}" y="${height - 8}" text-anchor="middle" fill="#6b7280" font-size="9">${esc(value.label)}</text><text x="${barX + barWidth / 2}" y="${barY - 5}" text-anchor="middle" fill="#9ca3af" font-size="9">${formatter(total)}</text>`;
    }).join('');
    const grid = [0, .5, 1].map((ratio) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${margin.top + plotHeight * ratio}" y2="${margin.top + plotHeight * ratio}" stroke="rgba(255,255,255,.06)"/>`).join('');
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Bar chart">${grid}${bars}</svg>`;
  }

  function renderCharts() {
    renderTemperatureChart();
    renderBars($('excursionChart'), data.buildExcursionSeries(events).slice(-12), { cold: '#60a5fa', warm: '#ef4444' }, (value) => value);
    const scenarios = Object.entries(data.buildScenarioCounts(events)).map(([label, count]) => ({ label, count }));
    renderBars($('scenarioChart'), scenarios, Object.values(SCENARIO_COLORS), (value) => value);
    $('scenarioLegend').innerHTML = scenarios.map((scenario) => `<span><i class="legend-dot" style="background:${SCENARIO_COLORS[scenario.label] || '#6b7280'}"></i>${esc(scenario.label)} ${scenario.count}</span>`).join('');
  }

  function renderTable(summaries) {
    $('sensorTable').innerHTML = summaries.map((sensor) => `<tr><td class="sensor-name">${esc(sensor.sensorName)}</td><td class="temp">${formatC(sensor.latestTemperatureC)}</td><td><span class="condition ${statusClass(sensor.status)}">${statusLabel(sensor.status)}</span></td><td class="muted-cell">${esc(sensor.latestScenario)}</td><td class="muted-cell">${sensor.readingCount}</td><td>${liveMode ? '<span class="muted-cell">Run selected</span>' : `<button class="row-action" type="button" data-focus-sensor="${esc(sensor.sensorName)}">View trend</button>`}</td></tr>`).join('');
    if (liveMode) return;
    $('sensorTable').querySelectorAll('[data-focus-sensor]').forEach((button) => button.addEventListener('click', () => {
      selectedSensors = [button.dataset.focusSensor, ...selectedSensors.filter((sensor) => sensor !== button.dataset.focusSensor)].slice(0, 6);
      render();
      $('trendCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
  }

  function renderProvenance() {
    const offsets = data.buildReplayOffsetSeries(events).filter((item) => Number.isFinite(item.hours));
    const average = offsets.length ? offsets.reduce((sum, item) => sum + item.hours, 0) / offsets.length : 0;
    $('provenanceValue').textContent = offsets.length ? `${Math.round(average).toLocaleString()} hours replay offset` : 'No source timestamps';
    $('provenanceFill').style.width = `${Math.min(100, Math.max(8, Math.abs(average) / 1000))}%`;
  }

  function render() {
    const summaries = data.summarizeSensors(events);
    const availableSensors = liveMode && runSensors?.length ? runSensors : summaries.map((sensor) => sensor.sensorName);
    renderPicker(availableSensors);
    renderKpis(summaries);
    renderAttention(summaries);
    renderStatusBars(summaries);
    renderCharts();
    renderTable(summaries);
    renderProvenance();
    $('dataMode').textContent = dataLabel;
    $('modePill').textContent = liveMode ? 'LIVE MQTT' : sourceLabel === 'LOCAL' ? 'DEMO SIMULATION' : 'IMPORTED FILE';
    $('profileName').textContent = profile.label;
    $('profileTarget').textContent = formatC(profile.targetC);
    $('profileRange').textContent = rangeText();
    $('trendSub').textContent = `${selectedSensors.length} sensor${selectedSensors.length === 1 ? '' : 's'} selected${liveMode ? ' in this live run' : ''} · fixed chart scale · threshold band ${rangeText()}`;
    $('chartHelp').textContent = liveMode ? 'Pods selected in Live runner' : 'Choose sensors below';
    $('targetLegend').textContent = `Target ${formatC(profile.targetC)}`;
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    const draw = () => { renderQueued = false; render(); };
    if (typeof global.requestAnimationFrame === 'function') global.requestAnimationFrame(draw); else setTimeout(draw, 16);
  }

  function applyLiveRun(status) {
    liveMode = true;
    liveRunId = status.run_id;
    events = [];
    runSensors = Array.isArray(status.sensors) && status.sensors.length ? status.sensors.slice() : DEFAULT_SENSORS.slice();
    selectedSensors = runSensors.slice();
    const bounds = { min_temp: status.min_temp, max_temp: status.max_temp };
    applyProfile(status.profile_id || 'pfizer_ultralow', bounds);
    dataLabel = `Live ${profile.label} run · waiting for events`;
    sourceLabel = 'LIVE';
    render();
  }

  function acceptLiveEvent(rawEvent) {
    if (!liveMode || !liveRunId || rawEvent.run_id !== liveRunId) return;
    events.push(data.normalizeEvent(rawEvent, profile));
    if (events.length > 12000) events = events.slice(-12000);
    queueRender();
  }

  function handleLiveStatus(status) {
    if (!liveMode || status.run_id !== liveRunId) return;
    if (!status.running && (status.state === 'completed' || status.state === 'stopped')) {
      dataLabel = `Live ${profile.label} run · ${events.length.toLocaleString()} events received`;
      render();
    }
  }

  $('resetButton').addEventListener('click', () => {
    liveMode = false;
    liveRunId = null;
    runSensors = null;
    applyProfile('pfizer_ultralow');
    events = data.createDemoEvents();
    selectedSensors = DEFAULT_SENSORS.slice();
    dataLabel = 'Using built-in demo events';
    sourceLabel = 'LOCAL';
    render();
    showToast('Demo data restored.');
  });
  $('exportButton').addEventListener('click', () => {
    const visible = events.filter((event) => selectedSensors.includes(event.sensor_name));
    const blob = new Blob([data.toCsv(visible)], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'vaccine-dashboard-view.csv';
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 0);
  });

  applyProfile('pfizer_ultralow');
  render();
  const observer = bridge?.createObserver({
    onHealth: (health) => setBridgeState(Boolean(health.mqtt_connected), health.mqtt_connected ? 'Live bridge connected' : 'Bridge online · MQTT offline'),
    onRunStart: applyLiveRun,
    onEvent: acceptLiveEvent,
    onStatus: handleLiveStatus,
  });
  observer?.start();
  global.VaccineDashboard = { getEvents: () => events.slice(), render, normalizeEvent: data.normalizeEvent };
})(typeof globalThis === 'undefined' ? this : globalThis);
