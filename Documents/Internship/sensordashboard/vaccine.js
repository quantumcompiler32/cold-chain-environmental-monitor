(function initVaccineDashboard(global) {
  const data = global.VaccineData;
  if (!data) return;

  const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#6b7280'];
  const SCENARIO_COLORS = { normal: '#10b981', recovery: '#3b82f6', outlier: '#f59e0b', failure: '#ef4444' };
  const DEFAULT_SENSORS = ['Pod1', 'Pod2', 'Pod3', 'Pod6', 'Pod11', 'Pod20'];
  let events = data.createDemoEvents();
  let selectedSensors = DEFAULT_SENSORS.slice();
  let dataLabel = 'Using built-in demo events';
  let sourceLabel = 'LOCAL DEMO';
  let toastTimer;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const formatC = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}°C` : '—';
  const statusLabel = (status) => ({ STABLE: 'Stable', ACCEPTABLE: 'Acceptable', TOO_COLD: 'Too cold', TOO_WARM: 'Too warm', UNKNOWN: 'No reading' }[status] || status);
  const statusClass = (status) => String(status || 'UNKNOWN').toLowerCase().replace('_', '-');
  const sorted = (list) => list.slice().sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp));

  function showToast(message) {
    const toast = $('toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
  }

  function setTab(name) {
    const analytics = name === 'analytics';
    $('analyticsTab').classList.toggle('active', analytics);
    $('rawTab').classList.toggle('active', !analytics);
    $('analyticsTab').setAttribute('aria-selected', String(analytics));
    $('rawTab').setAttribute('aria-selected', String(!analytics));
    $('panel-analytics').classList.toggle('active', analytics);
    $('panel-raw').classList.toggle('active', !analytics);
  }

  function uniqueSensors() {
    return data.summarizeSensors(events).map((sensor) => sensor.sensorName);
  }

  function renderKpis(summaries) {
    const inRange = summaries.filter((sensor) => sensor.status === 'STABLE' || sensor.status === 'ACCEPTABLE').length;
    const warmest = summaries.reduce((best, sensor) => !best || sensor.latestTemperatureC > best.latestTemperatureC ? sensor : best, null);
    const coldest = summaries.reduce((best, sensor) => !best || sensor.latestTemperatureC < best.latestTemperatureC ? sensor : best, null);
    const latestEvent = sorted(events).at(-1);
    $('kpiInRange').textContent = `${inRange}/${summaries.length}`;
    $('kpiInRangeDetail').textContent = inRange === summaries.length ? 'All package sensors acceptable' : `${summaries.length - inRange} sensor${summaries.length - inRange === 1 ? '' : 's'} need review`;
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
    $('attentionTitle').textContent = outOfRange.length ? `${outOfRange.length} package sensor${outOfRange.length === 1 ? '' : 's'} need review` : 'All package sensors are in range';
    $('attentionText').textContent = outOfRange.length ? `${names}${outOfRange.length > 3 ? ' and more' : ''} outside −80°C to −60°C. Check affected stock before use.` : 'The latest readings are within the documented Pfizer ultralow range.';
    $('reviewButton').textContent = outOfRange.length ? 'Review excursion' : 'View sensor table';
    $('reviewButton').onclick = () => {
      if (outOfRange.length) {
        selectedSensors = [outOfRange[0].sensorName, ...selectedSensors.filter((sensor) => sensor !== outOfRange[0].sensorName)].slice(0, 6);
        render();
      }
      $('sensorTableCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
  }

  function renderPicker(availableSensors) {
    const picker = $('sensorPicker');
    const active = selectedSensors.filter((sensor) => availableSensors.includes(sensor));
    selectedSensors = active.length ? active : availableSensors.slice(0, 6);
    picker.innerHTML = availableSensors.map((sensorName, index) => `<button class="sensor-chip${selectedSensors.includes(sensorName) ? ' selected' : ''}" type="button" aria-pressed="${selectedSensors.includes(sensorName)}" data-sensor="${esc(sensorName)}" style="--chip-color:${COLORS[index % COLORS.length]}">${esc(sensorName)}</button>`).join('');
    picker.querySelectorAll('[data-sensor]').forEach((button) => button.addEventListener('click', () => {
      const sensor = button.dataset.sensor;
      if (selectedSensors.includes(sensor)) {
        if (selectedSensors.length === 1) return showToast('Keep at least one sensor selected.');
        selectedSensors = selectedSensors.filter((item) => item !== sensor);
      } else {
        selectedSensors = [...selectedSensors, sensor];
      }
      render();
    }));
  }

  function linePath(values, x, y) {
    let path = '';
    let hasPrevious = false;
    values.forEach((value, index) => {
      if (value === null || value === undefined) {
        hasPrevious = false;
        return;
      }
      const command = hasPrevious ? 'L' : 'M';
      path += `${command}${x(index).toFixed(1)},${y(value).toFixed(1)} `;
      hasPrevious = true;
    });
    return path.trim();
  }

  function renderTemperatureChart() {
    const target = $('temperatureChart');
    const chart = data.buildChartSeries(events, selectedSensors);
    const width = Math.max(target.clientWidth || 620, 320);
    const height = 236;
    const margin = { top: 14, right: 12, bottom: 28, left: 40 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const min = -85;
    const max = -55;
    const x = (index) => margin.left + (chart.labels.length <= 1 ? plotWidth / 2 : index * plotWidth / (chart.labels.length - 1));
    const y = (value) => margin.top + (max - value) * plotHeight / (max - min);
    const yTicks = [-85, -80, -75, -70, -65, -60, -55];
    const xTicks = chart.labels.map((label, index) => ({ label, index })).filter((_, index) => index === 0 || index === chart.labels.length - 1 || index % Math.max(1, Math.floor(chart.labels.length / 5)) === 0);
    const grid = yTicks.map((tick) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(tick)}" y2="${y(tick)}" stroke="rgba(255,255,255,.06)"/><text x="${margin.left - 8}" y="${y(tick) + 3}" text-anchor="end" fill="#6b7280" font-size="10">${tick}°</text>`).join('');
    const labels = xTicks.map(({ label, index }) => `<text x="${x(index)}" y="${height - 7}" text-anchor="middle" fill="#6b7280" font-size="10">${esc(new Date(label).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))}</text>`).join('');
    const lines = chart.series.map((series, index) => `<path d="${linePath(series.values, x, y)}" fill="none" stroke="${COLORS[index % COLORS.length]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`).join('');
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Selected package temperature trend"><rect x="${margin.left}" y="${y(-60)}" width="${plotWidth}" height="${y(-80) - y(-60)}" fill="rgba(16,185,129,.1)"/><line x1="${margin.left}" x2="${width - margin.right}" y1="${y(-80)}" y2="${y(-80)}" stroke="rgba(96,165,250,.65)" stroke-dasharray="4 4"/><line x1="${margin.left}" x2="${width - margin.right}" y1="${y(-60)}" y2="${y(-60)}" stroke="rgba(239,68,68,.65)" stroke-dasharray="4 4"/><line x1="${margin.left}" x2="${width - margin.right}" y1="${y(data.PROFILE.targetC)}" y2="${y(data.PROFILE.targetC)}" stroke="#fbbf24" stroke-dasharray="2 4"/>${grid}${lines}${labels}</svg>`;
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
      const barHeight = total / max * plotHeight;
      return `<rect x="${barX}" y="${barY}" width="${barWidth}" height="${barHeight}" fill="${colors[index % colors.length]}" rx="3"/><text x="${barX + barWidth / 2}" y="${height - 8}" text-anchor="middle" fill="#6b7280" font-size="9">${esc(value.label)}</text><text x="${barX + barWidth / 2}" y="${barY - 5}" text-anchor="middle" fill="#9ca3af" font-size="9">${formatter(total)}</text>`;
    }).join('');
    const grid = [0, .5, 1].map((ratio) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${margin.top + plotHeight * ratio}" y2="${margin.top + plotHeight * ratio}" stroke="rgba(255,255,255,.06)"/>`).join('');
    target.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Bar chart">${grid}${bars}</svg>`;
  }

  function renderCharts() {
    renderTemperatureChart();
    const excursions = data.buildExcursionSeries(events).slice(-12);
    renderBars($('excursionChart'), excursions, { cold: '#60a5fa', warm: '#ef4444' }, (value) => value);
    const scenarios = Object.entries(data.buildScenarioCounts(events)).map(([label, count]) => ({ label, count }));
    renderBars($('scenarioChart'), scenarios, Object.values(SCENARIO_COLORS), (value) => value);
    $('scenarioLegend').innerHTML = scenarios.map((scenario) => `<span><i class="legend-dot" style="background:${SCENARIO_COLORS[scenario.label] || '#6b7280'}"></i>${esc(scenario.label)} ${scenario.count}</span>`).join('');
  }

  function renderTable(summaries) {
    $('sensorTable').innerHTML = summaries.map((sensor) => `<tr><td class="sensor-name">${esc(sensor.sensorName)}</td><td class="temp">${formatC(sensor.latestTemperatureC)}</td><td><span class="condition ${statusClass(sensor.status)}">${statusLabel(sensor.status)}</span></td><td class="muted-cell">${esc(sensor.latestScenario)}</td><td class="muted-cell">${sensor.readingCount}</td><td><button class="row-action" type="button" data-focus-sensor="${esc(sensor.sensorName)}">View trend</button></td></tr>`).join('');
    $('sensorTable').querySelectorAll('[data-focus-sensor]').forEach((button) => button.addEventListener('click', () => {
      selectedSensors = [button.dataset.focusSensor, ...selectedSensors.filter((sensor) => sensor !== button.dataset.focusSensor)].slice(0, 6);
      render();
      $('trendCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }));
  }

  function renderRaw() {
    const filter = $('rawSensorFilter').value;
    const visible = sorted(events).filter((event) => filter === 'all' || event.sensor_name === filter).slice(-80).reverse();
    $('rawStream').innerHTML = visible.map((event) => `<div class="raw-row"><span class="ts">[${esc(event.timestamp)}]</span> <span class="sid">${esc(event.sensor_name)}</span> { <span class="key">"temperature_c"</span>: <span class="${event.status === 'STABLE' || event.status === 'ACCEPTABLE' ? 'val' : 'crit'}">${event.temperature_c.toFixed(2)}</span>, <span class="key">"status"</span>: <span class="${event.status === 'STABLE' || event.status === 'ACCEPTABLE' ? 'val' : 'crit'}">"${esc(event.status)}"</span>, <span class="key">"scenario"</span>: <span class="val">"${esc(event.scenario)}"</span> }</div>`).join('');
    $('rowCount').textContent = visible.length;
    $('statIn').textContent = events.length.toLocaleString();
  }

  function renderProvenance() {
    const offsets = data.buildReplayOffsetSeries(events).filter((item) => Number.isFinite(item.hours));
    const average = offsets.length ? offsets.reduce((sum, item) => sum + item.hours, 0) / offsets.length : 0;
    $('provenanceValue').textContent = offsets.length ? `${Math.round(average).toLocaleString()} hours replay offset` : 'No source timestamps';
    $('provenanceFill').style.width = `${Math.min(100, Math.max(8, Math.abs(average) / 1000))}%`;
  }

  function render() {
    const summaries = data.summarizeSensors(events);
    const sensors = summaries.map((sensor) => sensor.sensorName);
    renderPicker(sensors);
    renderKpis(summaries);
    renderAttention(summaries);
    renderStatusBars(summaries);
    renderCharts();
    renderTable(summaries);
    renderProvenance();
    $('dataMode').textContent = dataLabel;
    $('rawMode').textContent = sourceLabel === 'LOCAL DEMO' ? 'DEMO' : 'FILE';
    $('rawSource').textContent = sourceLabel;
    const filter = $('rawSensorFilter');
    const current = filter.value;
    filter.innerHTML = `<option value="all">ALL PODS</option>${sensors.map((sensor) => `<option value="${esc(sensor)}">${esc(sensor)}</option>`).join('')}`;
    filter.value = sensors.includes(current) ? current : 'all';
    renderRaw();
  }

  function download(filename, content, type) {
    const blob = new Blob([content], { type });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 0);
  }

  function loadFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        events = data.parseTemperatureEvents(String(reader.result), file.name.toLowerCase().endsWith('.json') ? 'json' : 'csv');
        if (!events.length) throw new Error('No temperature events found');
        selectedSensors = data.summarizeSensors(events).slice(0, 6).map((sensor) => sensor.sensorName);
        dataLabel = `Loaded ${events.length.toLocaleString()} events from ${file.name}`;
        sourceLabel = file.name;
        render();
        showToast(`Loaded ${events.length.toLocaleString()} temperature events.`);
      } catch (error) {
        showToast(`Could not load file: ${error.message}`);
      }
    };
    reader.readAsText(file);
  }

  $('analyticsTab').addEventListener('click', () => setTab('analytics'));
  $('rawTab').addEventListener('click', () => setTab('raw'));
  $('rawSensorFilter').addEventListener('change', renderRaw);
  $('importButton').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', (event) => loadFile(event.target.files[0]));
  $('resetButton').addEventListener('click', () => {
    events = data.createDemoEvents();
    selectedSensors = DEFAULT_SENSORS.slice();
    dataLabel = 'Using built-in demo events';
    sourceLabel = 'LOCAL DEMO';
    render();
    showToast('Demo data restored.');
  });
  $('exportButton').addEventListener('click', () => {
    const visible = events.filter((event) => selectedSensors.includes(event.sensor_name));
    download('vaccine-dashboard-view.csv', data.toCsv(visible), 'text/csv;charset=utf-8');
    showToast(`Exported ${visible.length.toLocaleString()} selected-sensor events.`);
  });

  global.VaccineDashboard = { getEvents: () => events.slice(), render };
  render();
})(typeof globalThis === 'undefined' ? this : globalThis);
