(function initVaccineAnalytics(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#6b7280'];
  const SCENARIO_COLORS = { normal: '#10b981', recovery: '#3b82f6', mixed: '#8b5cf6', cooling_failure: '#ef4444', outlier: '#f59e0b', failure: '#ef4444' };
  const OPERATIONAL_STATUS_COLORS = { NORMAL: '#10b981', WARNING: '#f59e0b', CRITICAL: '#ef4444', SENSOR_FAULT: '#ef4444', OFFLINE: '#6b7280', EMPTY: '#60a5fa', ENERGY_WASTE: '#ec4899' };
  const OPERATIONAL_STATUS_ICONS = { NORMAL: '✓', WARNING: '!', CRITICAL: '!', SENSOR_FAULT: '⚠', OFFLINE: '×', EMPTY: '○', ENERGY_WASTE: '⚡' };
  const DEFAULT_SENSORS = ['Pod1', 'Pod2', 'Pod3', 'Pod6', 'Pod11', 'Pod20'];
  let events = [];
  let selectedSensors = [];
  let profile = data.PROFILE;
  let dataLabel = 'Waiting for PostgreSQL events';
  let renderQueued = false;
  let toastTimer;
  let stopWatching = null;
  let currentEndpoint = '/api/live';
  let responseScope = null;
  let activePodButton = null;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const formatC = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}°C` : '—';
  const eventTimeValue = (value) => { const parsed = Date.parse(String(value || '').replace(' ', 'T')); return Number.isFinite(parsed) ? parsed : 0; };
  const statusLabel = (status) => ({ STABLE: 'Stable', ACCEPTABLE: 'Acceptable', TOO_COLD: 'Too cold', TOO_WARM: 'Too warm', UNKNOWN: 'No reading' }[status] || status);
  const operationalLabel = (status) => data.operationalStatusLabel(status);
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

  function latestPodEvents() {
    const byPod = new Map();
    sorted(events).forEach((event) => byPod.set(event.sensor_name, event));
    return Array.from(byPod.values()).sort((left, right) => left.sensor_name.localeCompare(right.sensor_name, undefined, { numeric: true }));
  }

  function podClass(status) {
    return String(status || 'UNKNOWN').toLowerCase().replaceAll('_', '-');
  }

  function trendClass(trendKey) {
    return `trend-${String(trendKey || 'stable').replaceAll('_', '-')}`;
  }

  function renderPodMiniChart(summary) {
    const sourcePoints = summary.chartEvents || [];
    const sensorName = sourcePoints[0]?.sensor_name || summary.latest?.sensor_name;
    const compactChart = sensorName
      ? data.buildChartSeries(sourcePoints, [sensorName], { maxPoints: 24 })
      : { labels: [], series: [{ values: [] }] };
    const points = compactChart.labels.map((timestamp, index) => ({
      timestamp,
      temperature_c: compactChart.series[0]?.values[index],
    }));
    const width = 270;
    const height = 132;
    const margin = { top: 18, right: 8, bottom: 24, left: 38 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const values = points.map((event) => Number(event.temperature_c)).filter(Number.isFinite);
    const bounds = [profile.lowerLimitC, profile.upperLimitC, profile.targetC, ...values].filter(Number.isFinite);
    const rawMin = Math.min(...bounds, -80);
    const rawMax = Math.max(...bounds, -60);
    const padding = Math.max(1, (rawMax - rawMin) * 0.08);
    const min = rawMin - padding;
    const max = rawMax + padding;
    const x = (index) => margin.left + (points.length <= 1 ? plotWidth / 2 : index * plotWidth / (points.length - 1));
    const y = (value) => margin.top + (max - value) * plotHeight / (max - min);
    const path = points.map((event, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${y(Number(event.temperature_c)).toFixed(1)}`).join(' ');
    const yTicks = [];
    [profile.upperLimitC, profile.targetC, profile.lowerLimitC]
      .filter((value, index, list) => Number.isFinite(value) && list.indexOf(value) === index && value >= min && value <= max)
      .sort((left, right) => right - left)
      .forEach((tick) => {
        if (yTicks.every((existing) => Math.abs(y(existing) - y(tick)) >= 15)) yTicks.push(tick);
      });
    const grid = yTicks.map((tick) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(tick).toFixed(1)}" y2="${y(tick).toFixed(1)}" stroke="${tick === profile.targetC ? 'rgba(251,191,36,.45)' : 'rgba(255,255,255,.12)'}" stroke-dasharray="${tick === profile.targetC ? '2 3' : '4 4'}"/><text x="${margin.left - 6}" y="${(y(tick) + 3).toFixed(1)}" text-anchor="end" fill="#9ca3af" font-size="9">${Number(tick).toFixed(0)}°</text>`).join('');
    const firstTime = points[0] ? eventTimeValue(points[0].timestamp) : null;
    const lastTime = points.at(-1) ? eventTimeValue(points.at(-1).timestamp) : null;
    const elapsedMinutes = firstTime != null && lastTime != null ? Math.max(0, Math.round((lastTime - firstTime) / 60000)) : 0;
    const axis = `<line x1="${margin.left}" x2="${width - margin.right}" y1="${height - margin.bottom}" y2="${height - margin.bottom}" stroke="rgba(255,255,255,.2)"/><text x="${margin.left}" y="${height - 7}" fill="#6b7280" font-size="9">-${elapsedMinutes}m</text><text x="${width - margin.right}" y="${height - 7}" text-anchor="end" fill="#6b7280" font-size="9">now</text><text x="${width / 2}" y="${height - 7}" text-anchor="middle" fill="#6b7280" font-size="9">time</text><text x="10" y="${height / 2}" text-anchor="middle" transform="rotate(-90 10 ${height / 2})" fill="#6b7280" font-size="9">°C</text>`;
    const line = path ? `<path d="${path}" fill="none" stroke="${summary.trendKey === 'rapid_warming' || summary.trendKey === 'too_warm' ? '#fb7185' : summary.trendKey === 'rapid_cooling' || summary.trendKey === 'too_cold' ? '#60a5fa' : '#c4b5fd'}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>` : '';
    const empty = points.length ? '' : `<text x="${width / 2}" y="${height / 2}" text-anchor="middle" fill="#6b7280" font-size="10">Waiting for trend data</text>`;
    return `<svg class="pod-mini-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(summary.trendMessage)} over the last ${summary.chartWindowMinutes} minutes"><text x="${margin.left}" y="10" fill="#9ca3af" font-size="9">${summary.chartWindowMinutes} min context</text>${grid}${axis}${line}${empty}</svg>`;
  }

  function positionPodHover(button) {
    const card = button.querySelector('.pod-hover-card');
    if (!card) return;
    activePodButton = button;
    const rect = button.getBoundingClientRect();
    const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
    const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
    const cardWidth = Math.min(300, Math.max(220, viewportWidth - 24));
    const cardHeight = Math.max(card.offsetHeight, 280);
    const gap = 10;
    const canFitAbove = rect.top >= cardHeight + gap;
    const canFitBelow = viewportHeight - rect.bottom >= cardHeight + gap;
    const placeAbove = canFitAbove || !canFitBelow;
    const centerX = Math.min(
      Math.max(rect.left + rect.width / 2, cardWidth / 2 + 12),
      viewportWidth - cardWidth / 2 - 12,
    );
    card.classList.toggle('above', placeAbove);
    card.style.left = `${centerX}px`;
    card.style.top = `${placeAbove ? rect.top - gap : rect.bottom + gap}px`;
  }

  function renderPodGrid() {
    const target = $('podGrid');
    if (!target) return;
    const pods = latestPodEvents();
    target.innerHTML = pods.length ? pods.map((event) => {
      const history = sorted(events.filter((historyEvent) => historyEvent.sensor_name === event.sensor_name));
      const summary = data.buildPodSummary(history, profile);
      const status = summary.operationalStatus || event.operational_status || 'NORMAL';
      const attentionClass = summary.trendKey === 'stable' ? '' : ' needs-attention';
      return `<button class="pod-tile ${podClass(status)} ${trendClass(summary.trendKey)}${attentionClass}" type="button" data-pod="${esc(event.sensor_name)}" aria-label="${esc(event.sensor_name)} ${esc(operationalLabel(status))}: ${esc(summary.trendMessage)}">
        <span class="pod-tile-head"><span class="pod-id">${esc(event.sensor_name)}</span><span class="pod-icon" aria-hidden="true">${OPERATIONAL_STATUS_ICONS[status] || '?'}</span></span>
        <span class="pod-temperature">${formatC(event.temperature_c)}</span>
        <span class="pod-state">${esc(operationalLabel(status))} · ${esc(event.occupancy_state || 'loaded')}</span>
        <span class="pod-alert">${esc(summary.trendMessage)}</span>
        <span class="pod-hover-card" role="tooltip"><span class="pod-hover-title">${esc(summary.trendMessage)}</span>${renderPodMiniChart(summary)}<span class="pod-hover-meta">${Number.isFinite(summary.deltaC) ? `${summary.deltaC >= 0 ? '+' : ''}${summary.deltaC.toFixed(2)}°C over ${Math.round(summary.observedMinutes)} min` : 'No recent trend available'}</span><span class="pod-hover-action"><b>Next step</b> ${esc(summary.recommendation)}</span></span>
      </button>`;
    }).join('') : '<div class="detail-muted">No persisted Pods match this scope.</div>';
    target.querySelectorAll('[data-pod]').forEach((button) => {
      button.addEventListener('click', () => openPodDetails(button.dataset.pod));
      button.addEventListener('mouseenter', () => positionPodHover(button));
      button.addEventListener('focus', () => positionPodHover(button));
      button.addEventListener('mouseleave', () => {
        if (activePodButton === button) activePodButton = null;
      });
    });
  }

  function formatDateTime(value) {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString([], { dateStyle: 'medium', timeStyle: 'medium' });
  }

  function openPodDetails(sensorName) {
    const history = sorted(events.filter((event) => event.sensor_name === sensorName));
    const latest = history.at(-1);
    if (!latest) return;
    const summary = data.buildPodSummary(history, profile);
    const detail = $('podDetailBackdrop');
    const status = summary.operationalStatus || latest.operational_status || 'NORMAL';
    $('podDetailTitle').textContent = latest.sensor_name;
    $('podDetailStatus').textContent = `${OPERATIONAL_STATUS_ICONS[status] || '?'} ${operationalLabel(status)}`;
    $('podDetailStatus').style.background = `${OPERATIONAL_STATUS_COLORS[status] || '#6b7280'}22`;
    $('podDetailStatus').style.color = OPERATIONAL_STATUS_COLORS[status] || '#9ca3af';
    const deviation = Number.isFinite(Number(latest.temperature_c)) && Number.isFinite(Number(profile.targetC)) ? Number(latest.temperature_c) - Number(profile.targetC) : null;
    $('podDetailGrid').innerHTML = [
      ['Observed status', statusLabel(latest.status)],
      ['Rule status', operationalLabel(status)],
      ['Vaccine', latest.vaccine_label || latest.vaccine_type],
      ['Batch', latest.batch_id || 'None'],
      ['Occupancy', latest.occupancy_state || 'loaded'],
      ['Current temperature', formatC(latest.temperature_c)],
      ['Safe range', `${formatC(latest.storage_min_c)} to ${formatC(latest.storage_max_c)}`],
      ['Deviation', deviation == null ? '—' : `${deviation >= 0 ? '+' : ''}${deviation.toFixed(2)}°C from target`],
      ['Scenario', latest.scenario],
      ['Phase', latest.scenario_phase || '—'],
      ['Trend', summary.trendMessage],
      ['Next step', summary.recommendation],
      ['Last event', formatDateTime(latest.event_time)],
    ].map(([label, value]) => `<div><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join('');
    $('podDetailTrend').innerHTML = `${renderPodMiniChart(summary)}<div class="detail-muted">${esc(summary.trendMessage)} · ${esc(summary.recommendation)}</div>`;
    $('podDetailAlerts').innerHTML = latest.rule_alert
      ? `<div class="detail-alert">${esc(latest.rule_alert.replaceAll('_', ' '))}<br><small>Severity: ${esc(latest.severity || 'warning')}</small></div>`
      : '<div class="detail-ok">No active rule-based alerts.</div>';
    detail.hidden = false;
  }

  function populateFilterOptions() {
    const values = {
      filterPod: [...new Set(events.map((event) => event.sensor_name).filter(Boolean))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
      filterVaccine: [...new Set(events.map((event) => event.vaccine_type).filter(Boolean))].sort(),
    };
    Object.entries(values).forEach(([id, options]) => {
      const select = $(id);
      if (!select) return;
      const current = select.value;
      select.innerHTML = `<option value="">All ${id === 'filterPod' ? 'Pods' : 'vaccines'}</option>` + options.map((option) => `<option value="${esc(option)}">${esc(option)}</option>`).join('');
      select.value = current;
    });
  }

  function scopeText(payload) {
    const scope = payload?.scope || responseScope;
    if (!scope) return 'Live · current persisted events';
    const start = scope.effective_start ? formatDateTime(scope.effective_start) : 'beginning';
    const end = scope.effective_end ? formatDateTime(scope.effective_end) : 'now';
    return `${currentEndpoint.startsWith('/api/live') ? 'Live' : 'Historical'} · ${start} → ${end}`;
  }

  function restartWatch(path = '/api/live/stream') {
    if (stopWatching) stopWatching();
    currentEndpoint = path;
    stopWatching = bridge.watchDatabase(
      (rawEvents, payload) => {
        events = rawEvents.map((event) => data.normalizeEvent(event));
        responseScope = payload?.scope || null;
        dataLabel = events.length.toLocaleString() + ' persisted PostgreSQL event' + (events.length === 1 ? '' : 's');
        populateFilterOptions();
        setBridgeState(true, path.startsWith('/api/live') ? 'Live PostgreSQL connected' : 'Historical PostgreSQL connected');
        render();
      },
      (error) => {
        events = [];
        dataLabel = 'PostgreSQL unavailable';
        setBridgeState(false, 'PostgreSQL unavailable');
        render();
        showToast(error.message);
      },
      path,
    );
  }

  function inputDate(value) {
    const date = new Date(value);
    const offset = date.getTimezoneOffset();
    return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
  }

  function applyRange(range) {
    document.querySelectorAll('[data-range]').forEach((button) => button.classList.toggle('active', button.dataset.range === range));
    if (range === 'live') {
      $('filterStart').value = '';
      $('filterEnd').value = '';
      restartWatch('/api/live/stream');
      return;
    }
    const end = new Date();
    const start = new Date(end);
    if (range === 'today') start.setHours(0, 0, 0, 0);
    if (range === '6h') start.setHours(start.getHours() - 6);
    if (range === '24h') start.setHours(start.getHours() - 24);
    if (range === 'week') { start.setDate(start.getDate() - ((start.getDay() + 6) % 7)); start.setHours(0, 0, 0, 0); }
    if (range === 'month') { start.setDate(1); start.setHours(0, 0, 0, 0); }
    $('filterStart').value = inputDate(start);
    $('filterEnd').value = inputDate(end);
    applyFilters();
  }

  function applyFilters() {
    const params = new URLSearchParams();
    [['start', 'filterStart'], ['end', 'filterEnd'], ['pod', 'filterPod'], ['vaccine', 'filterVaccine'], ['batch', 'filterBatch'], ['scenario', 'filterScenario'], ['severity', 'filterSeverity']].forEach(([name, id]) => {
      const value = $(id)?.value;
      if (value) params.set(name, id === 'filterStart' || id === 'filterEnd' ? new Date(value).toISOString() : value);
    });
    restartWatch('/api/events' + (params.toString() ? `?${params.toString()}` : ''));
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
    const borderline = events.filter((event) => String(event.uncertainty_status || '').startsWith('BORDERLINE')).length;
    $('kpiInRange').textContent = `${inRange}/${summaries.length}`;
    $('kpiInRangeDetail').textContent = inRange === summaries.length ? 'All package sensors acceptable' : `${summaries.length - inRange} sensor${summaries.length - inRange === 1 ? '' : 's'} outside range`;
    $('kpiWarmest').textContent = formatC(warmest?.latestTemperatureC);
    $('kpiWarmestDetail').textContent = warmest ? `${warmest.sensorName} · ${statusLabel(warmest.status)}` : 'No readings';
    $('kpiColdest').textContent = formatC(coldest?.latestTemperatureC);
    $('kpiColdestDetail').textContent = coldest ? `${coldest.sensorName} · ${statusLabel(coldest.status)}` : 'No readings';
    $('kpiEvents').textContent = events.length.toLocaleString();
    $('kpiEventsDetail').textContent = latestEvent ? `Latest event ${new Date(latestEvent.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'No readings';
    $('kpiBorderline').textContent = borderline.toLocaleString();
    $('kpiBorderlineDetail').textContent = borderline ? 'Possible storage-boundary overlap' : 'No boundary overlap detected';
  }

  function renderAttention(summaries) {
    const attention = $('attentionBanner');
    const outOfRange = summaries.filter((sensor) => sensor.status === 'TOO_COLD' || sensor.status === 'TOO_WARM');
    const names = outOfRange.slice(0, 3).map((sensor) => sensor.sensorName).join(', ');
    attention.classList.toggle('safe', outOfRange.length === 0);
    $('attentionTitle').textContent = outOfRange.length
      ? outOfRange.length + ' sensor' + (outOfRange.length === 1 ? '' : 's') + ' outside the stored profile range'
      : 'All stored sensors are in range';
    $('attentionText').textContent = outOfRange.length
      ? names + (outOfRange.length > 3 ? ' and more' : '') + ' require review.'
      : events.length ? 'The latest persisted readings are within their configured storage ranges.' : 'Waiting for persisted PostgreSQL readings.';
  }

  function renderPicker(availableSensors) {
    const active = selectedSensors.filter((sensor) => availableSensors.includes(sensor));
    selectedSensors = active.length ? active : availableSensors.slice(0, 6);
    const picker = $('sensorPicker');
    picker.innerHTML = availableSensors.map((sensorName, index) => '<button class="sensor-chip' + (selectedSensors.includes(sensorName) ? ' selected' : '') + '" type="button" aria-pressed="' + selectedSensors.includes(sensorName) + '" data-sensor="' + esc(sensorName) + '" style="--chip-color:' + COLORS[index % COLORS.length] + '">' + esc(sensorName) + '</button>').join('');
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
    const chart = data.buildChartSeries(events, selectedSensors, { maxPoints: 180 });
    const width = Math.max(target.clientWidth || 620, 320);
    const height = 340;
    target.style.height = `${height}px`;
    const margin = { top: 14, right: 12, bottom: 28, left: 40 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const observed = chart.series.flatMap((series) => series.values).filter(Number.isFinite);
    const observedMin = observed.length ? Math.min(...observed) : profile.targetC;
    const observedMax = observed.length ? Math.max(...observed) : profile.targetC;
    const observedSpan = Math.max(observedMax - observedMin, 0.2);
    const padding = Math.max(0.35, observedSpan * 0.25);
    let min = observedMin - padding;
    let max = observedMax + padding;
    const thresholds = [profile.lowerLimitC, profile.upperLimitC, profile.targetC];
    thresholds.forEach((threshold) => {
      const closeToData = threshold >= observedMin - 3 && threshold <= observedMax + 3;
      const nearestViolatedBoundary = observedMax < profile.lowerLimitC ? threshold === profile.lowerLimitC : observedMin > profile.upperLimitC ? threshold === profile.upperLimitC : false;
      if (closeToData || nearestViolatedBoundary) {
        min = Math.min(min, threshold - padding * 0.2);
        max = Math.max(max, threshold + padding * 0.2);
      }
    });
    const x = (index) => margin.left + (chart.labels.length <= 1 ? plotWidth / 2 : index * plotWidth / (chart.labels.length - 1));
    const y = (value) => margin.top + (max - value) * plotHeight / (max - min);
    const yTicks = Array.from({ length: 7 }, (_, index) => min + (max - min) * index / 6).reverse();
    const xTicks = chart.labels.map((label, index) => ({ label, index })).filter((_, index) => index === 0 || index === chart.labels.length - 1 || index % Math.max(1, Math.floor(chart.labels.length / 5)) === 0);
    const grid = yTicks.map((tick) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(tick)}" y2="${y(tick)}" stroke="rgba(255,255,255,.06)"/><text x="${margin.left - 8}" y="${y(tick) + 3}" text-anchor="end" fill="#6b7280" font-size="10">${tick.toFixed(1)}°</text>`).join('');
    const labels = xTicks.map(({ label, index }) => `<text x="${x(index)}" y="${height - 7}" text-anchor="middle" fill="#6b7280" font-size="10">${esc(new Date(label).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))}</text>`).join('');
    const lines = chart.series.map((series, index) => `<path d="${linePath(series.values, x, y)}" fill="none" stroke="${COLORS[index % COLORS.length]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`).join('');
    const bandTop = Math.min(max, profile.upperLimitC);
    const bandBottom = Math.max(min, profile.lowerLimitC);
    const band = bandBottom > bandTop ? `<rect x="${margin.left}" y="${y(bandTop)}" width="${plotWidth}" height="${y(bandBottom) - y(bandTop)}" fill="rgba(16,185,129,.1)"/>` : '';
    const lowerLine = profile.lowerLimitC >= min && profile.lowerLimitC <= max ? `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(profile.lowerLimitC)}" y2="${y(profile.lowerLimitC)}" stroke="rgba(96,165,250,.65)" stroke-dasharray="4 4"/>` : '';
    const upperLine = profile.upperLimitC >= min && profile.upperLimitC <= max ? `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(profile.upperLimitC)}" y2="${y(profile.upperLimitC)}" stroke="rgba(239,68,68,.65)" stroke-dasharray="4 4"/>` : '';
    const targetLine = profile.targetC >= min && profile.targetC <= max ? `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(profile.targetC)}" y2="${y(profile.targetC)}" stroke="#fbbf24" stroke-dasharray="2 4"/>` : '';
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Selected package temperature trend">${band}${lowerLine}${upperLine}${targetLine}${grid}${lines}${labels}</svg>`;
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

  function renderGroupedBars(target, values, groups) {
    const width = Math.max(target.clientWidth || 420, 280);
    const height = 170;
    const margin = { top: 12, right: 12, bottom: 30, left: 28 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const max = Math.max(...values.flatMap((value) => groups.map((group) => value[group.key] || 0)), 1);
    const groupWidth = plotWidth / Math.max(values.length, 1);
    const barWidth = Math.max(8, groupWidth / (groups.length + 1));
    const bars = values.map((value, index) => groups.map((group, groupIndex) => {
      const amount = value[group.key] || 0;
      const x = margin.left + index * groupWidth + (groupIndex + 0.5) * barWidth;
      const barHeight = amount / max * plotHeight;
      const y = margin.top + plotHeight - barHeight;
      return `<rect x="${x}" y="${y}" width="${barWidth - 2}" height="${barHeight}" fill="${group.color}" rx="2"><title>${esc(value.label)} ${esc(group.label)}: ${amount}</title></rect>`;
    }).join(`<text x="${margin.left + index * groupWidth + groupWidth / 2}" y="${height - 8}" text-anchor="middle" fill="#6b7280" font-size="9">${esc(value.label)}</text>`)).join('');
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Grouped comparison chart"><line x1="${margin.left}" x2="${width - margin.right}" y1="${margin.top + plotHeight}" y2="${margin.top + plotHeight}" stroke="rgba(255,255,255,.12)"/>${bars}</svg>`;
  }

  function renderSensorSpread(target, values) {
    const width = Math.max(target.clientWidth || 420, 280);
    const height = 170;
    const margin = { top: 12, right: 12, bottom: 30, left: 40 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    if (!values.length) {
      target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Sensor variation chart"><text x="${width / 2}" y="${height / 2}" text-anchor="middle" fill="#6b7280" font-size="11">Waiting for readings</text></svg>`;
      return;
    }
    const all = values.flatMap((value) => [value.minimum, value.average, value.maximum]);
    const low = Math.min(...all) - 0.5;
    const high = Math.max(...all) + 0.5;
    const x = (index) => margin.left + (values.length <= 1 ? plotWidth / 2 : index * plotWidth / (values.length - 1));
    const y = (value) => margin.top + (high - value) * plotHeight / (high - low);
    const lines = values.map((value, index) => `<line x1="${x(index)}" x2="${x(index)}" y1="${y(value.minimum)}" y2="${y(value.maximum)}" stroke="#8b5cf6" stroke-width="5" stroke-linecap="round"/><circle cx="${x(index)}" cy="${y(value.average)}" r="4" fill="#10b981"/><text x="${x(index)}" y="${height - 8}" text-anchor="middle" fill="#6b7280" font-size="9">${esc(value.label)}</text>`).join('');
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Minimum average maximum temperature by sensor">${lines}</svg>`;
  }

  function renderCharts() {
    renderTemperatureChart();
    renderBars($('excursionChart'), data.buildExcursionSeries(events).slice(-12), { cold: '#60a5fa', warm: '#ef4444' }, (value) => value);
    const scenarioCounts = data.buildScenarioCounts(events);
    const scenarioLabels = [...new Set(Object.keys(scenarioCounts))];
    const scenarios = scenarioLabels.map((label) => ({ label, count: scenarioCounts[label] || 0 }));
    renderBars($('scenarioChart'), scenarios, Object.values(SCENARIO_COLORS), (value) => value);
    const coverage = {};
    $('scenarioLegend').innerHTML = scenarios.map((scenario) => {
      const expected = coverage[scenario.label]?.expected;
      const label = Number.isFinite(expected) ? `${scenario.count}/${expected}` : `${scenario.count}`;
      return `<span><i class="legend-dot" style="background:${SCENARIO_COLORS[scenario.label] || '#6b7280'}"></i>${esc(data.scenarioDisplayLabel(scenario.label))} ${label}</span>`;
    }).join('');
    const received = scenarios.reduce((sum, scenario) => sum + scenario.count, 0);
    const expected = Object.values(coverage).reduce((sum, item) => sum + Number(item.expected || 0), 0);
    $('scenarioCoverageSummary').textContent = expected
      ? `${received.toLocaleString()} of ${expected.toLocaleString()} expected events received · normal stays in range`
      : 'Normal stays in range; other scenarios test excursions and recovery.';
    renderGroupedBars($('scenarioOutcomeChart'), data.buildScenarioOutcomeSeries(events), [
      { key: 'tooCold', label: 'Cold/warm excursions', color: '#ef4444' },
      { key: 'tooWarm', label: 'Warm excursions', color: '#f59e0b' },
      { key: 'borderline', label: 'Borderline', color: '#ec4899' },
    ]);
    const profileCounts = {};
    events.forEach((event) => { profileCounts[event.vaccine_type] = (profileCounts[event.vaccine_type] || 0) + 1; });
    const profileEntries = Object.entries(profileCounts).map(([id, count]) => ({ label: data.getProfile(id).label, count }));
    renderBars($('profileChart'), profileEntries, COLORS, (value) => value);
    $('profileLegend').innerHTML = profileEntries.map((item, index) => `<span><i class="legend-dot" style="background:${COLORS[index % COLORS.length]}"></i>${esc(item.label)} ${item.count}</span>`).join('');
    renderSensorSpread($('sensorSpreadChart'), data.buildSensorSpreadSeries(events, selectedSensors));
    renderGroupedBars($('uncertaintyChart'), data.buildUncertaintySeries(events).slice(-12), [
      { key: 'crossing', label: 'Boundary crossing', color: '#ec4899' },
      { key: 'borderline', label: 'Borderline', color: '#8b5cf6' },
    ]);
  }

  function renderTable(summaries) {
    $('sensorTable').innerHTML = summaries.map((sensor) => {
      const scenario = sensor.latestPhase ? `${sensor.latestScenario} · ${sensor.latestPhase}` : sensor.latestScenario;
      return '<tr><td class="sensor-name">' + esc(sensor.sensorName) + '</td><td class="temp">' + formatC(sensor.latestTemperatureC) + '</td><td><span class="condition ' + statusClass(sensor.status) + '">' + statusLabel(sensor.status) + '</span></td><td class="muted-cell">' + esc(scenario) + '</td><td class="muted-cell">' + sensor.readingCount + '</td><td><button class="row-action" type="button" data-focus-sensor="' + esc(sensor.sensorName) + '">View trend</button></td></tr>';
    }).join('');
    $('sensorTable').querySelectorAll('[data-focus-sensor]').forEach((button) => button.addEventListener('click', () => {
      selectedSensors = [button.dataset.focusSensor, ...selectedSensors.filter((sensor) => sensor !== button.dataset.focusSensor)].slice(0, 6);
      render();
      $('trendCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
  }

  function render() {
    const summaries = data.summarizeSensors(events);
    const availableSensors = summaries.map((sensor) => sensor.sensorName);
    const profileIds = [...new Set(events.map((event) => event.vaccine_type).filter(Boolean))];
    profile = data.getProfile(profileIds[0] || 'pfizer_ultralow');
    renderPicker(availableSensors);
    renderPodGrid();
    renderKpis(summaries);
    renderAttention(summaries);
    renderStatusBars(summaries);
    renderCharts();
    renderTable(summaries);
    const borderline = events.filter((event) => String(event.uncertainty_status || '').startsWith('BORDERLINE')).length;
    const crossing = events.filter((event) => event.boundary_crossing).length;
    $('uncertaintySummary').textContent = '±' + data.SENSOR_TOLERANCE_C.toFixed(1) + '°C Type-T accuracy';
    $('uncertaintyCopy').textContent = borderline.toLocaleString() + ' borderline reading' + (borderline === 1 ? '' : 's') + ' and ' + crossing.toLocaleString() + ' possible boundary crossing' + (crossing === 1 ? '' : 's') + ' in the stored database events.';
    $('dataMode').textContent = dataLabel;
    $('modePill').textContent = 'POSTGRESQL';
    $('profileName').textContent = profileIds.length > 1 ? 'Multiple vaccine profiles' : profile.label;
    $('profileTarget').textContent = profileIds.length > 1 ? 'Profile-specific' : formatC(profile.targetC);
    $('profileRange').textContent = profileIds.length > 1 ? 'Profile-specific' : rangeText();
    $('trendSub').textContent = selectedSensors.length + ' sensor' + (selectedSensors.length === 1 ? '' : 's') + ' selected · persisted database readings';
    $('chartHelp').textContent = 'Choose sensors below';
    $('targetLegend').textContent = 'Target ' + formatC(profile.targetC);
    $('effectiveRange').textContent = scopeText(responseScope);
  }

  function queueRender() {
    if (renderQueued) return;
    renderQueued = true;
    const draw = () => { renderQueued = false; render(); };
    if (typeof global.requestAnimationFrame === 'function') global.requestAnimationFrame(draw); else setTimeout(draw, 16);
  }

  window.addEventListener('scroll', () => {
    if (activePodButton) positionPodHover(activePodButton);
  }, true);
  window.addEventListener('resize', () => {
    if (activePodButton) positionPodHover(activePodButton);
  });

  $('exportButton').addEventListener('click', async () => {
    try {
      await bridge.exportAllEvents();
      showToast('Exported all PostgreSQL events.');
    } catch (error) {
      showToast(error.message);
    }
  });

  $('exportColabButton').addEventListener('click', async () => {
    try {
      await bridge.exportColabTrainingCsv();
      showToast('Downloaded Test1_TempCO2O2.csv for Colab.');
    } catch (error) {
      showToast(error.message);
    }
  });

  document.querySelectorAll('[data-range]').forEach((button) => button.addEventListener('click', () => applyRange(button.dataset.range)));
  $('applyFilters').addEventListener('click', () => {
    document.querySelectorAll('[data-range]').forEach((button) => button.classList.remove('active'));
    applyFilters();
  });
  $('clearFilters').addEventListener('click', () => {
    ['filterStart', 'filterEnd', 'filterBatch', 'filterPod', 'filterVaccine', 'filterScenario', 'filterSeverity'].forEach((id) => { if ($(id)) $(id).value = ''; });
    applyRange('live');
  });
  $('closePodDetail').addEventListener('click', () => { $('podDetailBackdrop').hidden = true; });
  $('podDetailBackdrop').addEventListener('click', (event) => { if (event.target.id === 'podDetailBackdrop') event.currentTarget.hidden = true; });

  applyProfile('pfizer_ultralow');
  render();
  restartWatch('/api/live/stream');
})(typeof globalThis === 'undefined' ? this : globalThis);
