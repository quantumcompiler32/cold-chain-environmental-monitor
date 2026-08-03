(function runPhase1App(global) {
  const adapterFactory = global.Phase1Adapter;
  const bridge = global.VaccineBridge;
  const data = global.VaccineData;
  const inference = global.Phase1Inference;
  if (!adapterFactory || !bridge || !data || !inference) return;

  const app = document.getElementById('app');
  const connectionBadge = document.getElementById('connectionBadge');
  const toast = document.getElementById('toast');
  const adapter = adapterFactory.createPhase1Adapter([], { connection: 'offline' });
  const state = { route: 'operations', filters: { pod: 'all', scenario: 'all', timeRange: 'all' }, follow: true, expanded: new Set(), analysis: null, analysisKey: null, inferenceDraft: null, inferenceResult: null, inferenceError: null, inferenceBusy: false, lastEventId: null, toastTimer: null };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const temperature = (value) => value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(1)}°C`;
  const timestamp = (value) => { const date = new Date(value); return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }); };
  const statusClass = (status) => status === 'TOO_WARM' ? 'warm' : status === 'TOO_COLD' ? 'cold' : status === 'UNKNOWN' ? 'unknown' : 'good';
  const statusLabel = (status) => ({ STABLE: 'In range', ACCEPTABLE: 'Acceptable', TOO_COLD: 'Too cold', TOO_WARM: 'Too warm', UNKNOWN: 'No reading' }[status] || status || 'Unknown');

  function notify(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
  }

  function setConnection(status) {
    const online = status === 'connected';
    connectionBadge.classList.toggle('offline', !online);
    connectionBadge.classList.toggle('online', online);
    connectionBadge.querySelector('span').textContent = online ? 'POSTGRESQL CONNECTED' : 'POSTGRESQL OFFLINE';
  }

  function filterControls(options) {
    const option = (value, label, selected) => `<option value="${esc(value)}" ${value === selected ? 'selected' : ''}>${esc(label)}</option>`;
    return `<div class="toolbar-group"><label for="podFilter">Pod</label><select class="field" id="podFilter" data-filter="pod">${option('all', 'All Pods', state.filters.pod)}${options.pods.map((pod) => option(pod, pod, state.filters.pod)).join('')}</select></div>` +
      `<div class="toolbar-group"><label for="scenarioFilter">Scenario</label><select class="field" id="scenarioFilter" data-filter="scenario">${option('all', 'All scenarios', state.filters.scenario)}${options.scenarios.map((scenario) => option(scenario, scenario, state.filters.scenario)).join('')}</select></div>` +
      `<div class="toolbar-group"><label for="timeFilter">Time range</label><select class="field" id="timeFilter" data-filter="timeRange">${option('all', 'All available', state.filters.timeRange)}${option('24', 'Last 24 hours', state.filters.timeRange)}${option('168', 'Last 7 days', state.filters.timeRange)}${option('720', 'Last 30 days', state.filters.timeRange)}</select></div>`;
  }

  function analysisKey(view) {
    const latest = view.events.at(-1);
    return JSON.stringify({ filters: state.filters, count: view.events.length, latest: latest ? `${latest.event_id}:${latest.timestamp}` : null });
  }

  function renderStatusStrip(view) {
    const latest = view.metrics.latestEvent;
    return `<section class="status-strip" aria-label="Current cold-chain status">
      <div class="status-cell"><span class="label">Active excursions</span><strong class="${view.metrics.activeExcursions ? 'alert' : 'good'}">${view.metrics.activeExcursions}</strong><small>Pods needing review</small></div>
      <div class="status-cell"><span class="label">Pods reporting</span><strong>${view.metrics.podsReporting}/${view.metrics.expectedPods}</strong><small>Persisted telemetry</small></div>
      <div class="status-cell"><span class="label">Readings in range</span><strong class="${view.metrics.readingsInRangePercent === null ? '' : 'good'}">${view.metrics.readingsInRangePercent === null ? '—' : `${view.metrics.readingsInRangePercent}%`}</strong><small>Current Pod status</small></div>
      <div class="status-cell"><span class="label">Latest event</span><strong>${latest ? timestamp(latest.timestamp).split(', ').slice(-1)[0] : '—'}</strong><small>${latest ? esc(latest.sensor_name) : 'Waiting for data'}</small></div>
      <div class="status-cell"><span class="label">Batches pending review</span><strong>—</strong><small>No stock linkage in event stream</small></div>
    </section>`;
  }

  function renderTrend(events, selectedPod) {
    const profile = events[0] ? data.getProfile(events[0].vaccine_type, events[0]) : data.getProfile();
    const sensors = [...new Set(events.map((event) => event.sensor_name))].sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));
    const plottedSensors = selectedPod !== 'all' ? sensors : sensors.slice(0, 6);
    const series = plottedSensors.map((sensor) => events.filter((event) => event.sensor_name === sensor).slice(-36));
    const values = events.map((event) => Number(event.temperature_c)).filter(Number.isFinite);
    if (!values.length) return `<div class="empty"><strong>No temperature trend available</strong>${selectedPod !== 'all' ? `No persisted readings match ${esc(selectedPod)}.` : 'The PostgreSQL bridge is waiting for persisted Pod readings.'}</div>`;
    const min = Math.min(profile.lowerLimitC, ...values) - 1;
    const max = Math.max(profile.upperLimitC, ...values) + 1;
    const width = 1000; const height = 300; const left = 54; const right = 980; const top = 18; const bottom = 260;
    const x = (index, count) => left + (count <= 1 ? (right - left) / 2 : index * (right - left) / (count - 1));
    const y = (value) => bottom - ((value - min) / Math.max(max - min, 1)) * (bottom - top);
    const colors = ['#d0bcff', '#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#a4c9ff'];
    const grid = [min, (min + max) / 2, max].map((value) => `<line class="chart-grid" x1="${left}" x2="${right}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-text" x="${left - 9}" y="${y(value) + 4}" text-anchor="end">${value.toFixed(1)}°</text>`).join('');
    const paths = series.map((items, seriesIndex) => {
      const points = items.map((event, index) => `${x(index, items.length).toFixed(1)},${y(Number(event.temperature_c)).toFixed(1)}`).join(' ');
      return `<polyline class="line ${seriesIndex === 1 ? 'cold' : seriesIndex === 4 ? 'warm' : ''}" points="${points}"><title>${esc(plottedSensors[seriesIndex])}</title></polyline>`;
    }).join('');
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Temperature trend for ${esc(selectedPod === 'all' ? 'selected Pods' : selectedPod)}"><rect class="safe-band" x="${left}" y="${y(profile.upperLimitC)}" width="${right - left}" height="${Math.max(1, y(profile.lowerLimitC) - y(profile.upperLimitC))}"/><line class="threshold" x1="${left}" x2="${right}" y1="${y(profile.lowerLimitC)}" y2="${y(profile.lowerLimitC)}"/><line class="threshold" x1="${left}" x2="${right}" y1="${y(profile.upperLimitC)}" y2="${y(profile.upperLimitC)}"/><line class="target" x1="${left}" x2="${right}" y1="${y(profile.targetC)}" y2="${y(profile.targetC)}"/>${grid}${paths}<text class="chart-text" x="${left}" y="${height - 9}">Suggested range ${profile.lowerLimitC}°C to ${profile.upperLimitC}°C · target ${profile.targetC}°C</text></svg>`;
  }

  function renderScenarioCoverage(counts) {
    const values = { normal: counts.normal || 0, outlier: counts.outlier || 0, failure: counts.failure || 0, recovery: counts.recovery || 0 };
    const total = Math.max(Object.values(values).reduce((sum, value) => sum + value, 0), 1);
    const descriptions = { normal: 'Safe baseline', outlier: 'Brief boundary crossing', failure: 'Sustained warm excursion', recovery: 'Returns toward target' };
    return `<div class="scenario-bar">${Object.entries(values).map(([name, value]) => `<span class="${name}" style="width:${value / total * 100}%" title="${name}: ${value}"></span>`).join('')}</div><div class="scenario-legend">${Object.entries(values).map(([name, value]) => `<div><b><i class="${name}"></i>${name} · ${value.toLocaleString()}</b>${descriptions[name]}</div>`).join('')}</div>`;
  }

  function renderConfidence(view) {
    return `<section class="panel"><div class="panel-heading"><div><span class="kicker">DATA CONFIDENCE</span><h3>Borderline readings need context</h3><p>Sensor uncertainty stays separate from raw event status.</p></div><strong class="model-value">${view.borderlineReadings.toLocaleString()}</strong></div><div class="confidence-grid">${view.packages.map((item) => `<div class="confidence-tile ${statusClass(item.status)}"><b>${esc(item.name)}</b><small>${item.status === 'UNKNOWN' ? 'No reading' : statusLabel(item.status)} · ${item.readings} readings</small></div>`).join('')}</div><div class="legend"><span><i></i>In range</span><span><i class="cold"></i>Too cold</span><span><i class="warm"></i>Too warm</span><span><i class="unknown"></i>No reading</span></div></section>`;
  }

  function renderOperations() {
    adapter.setFilters(state.filters);
    const view = adapter.operationsView();
    return `<div class="page-header"><div><span class="eyebrow">POD OPERATIONS · LIVE EVIDENCE</span><h1>What needs attention now?</h1><p>Monitor the paper-derived Pod channels, inspect the evidence, and keep every stock decision with a qualified human reviewer.</p></div><div class="page-actions"><button class="button" data-export>Export PostgreSQL CSV</button><span class="mono-label">${view.connection === 'connected' ? 'READ-ONLY BRIDGE' : 'DATA UNAVAILABLE'}</span></div></div>
      ${renderStatusStrip(view)}
      <div class="metric-grid"><div class="metric green"><span class="label">Packages in range</span><strong>${view.metrics.readingsInRangePercent === null ? '—' : `${view.metrics.readingsInRangePercent}%`}</strong><small>${view.metrics.podsReporting}/20 reporting</small></div><div class="metric amber"><span class="label">Warmest package</span><strong>${temperature(Math.max(...view.packages.map((item) => Number.isFinite(item.temperatureC) ? item.temperatureC : -Infinity)))}</strong><small>from current readings</small></div><div class="metric blue"><span class="label">Coldest package</span><strong>${temperature(Math.min(...view.packages.map((item) => Number.isFinite(item.temperatureC) ? item.temperatureC : Infinity)))}</strong><small>from current readings</small></div><div class="metric"><span class="label">Temperature events</span><strong>${view.metrics.totalEvents.toLocaleString()}</strong><small>selected scope</small></div></div>
      <div class="toolbar">${filterControls(view.options)}<span class="subtle">${view.connection === 'connected' ? 'Refreshes every 5 seconds' : 'Start the read-only bridge to load events'}</span></div>
      <div class="ops-grid"><div class="stack"><section class="panel"><div class="panel-heading"><div><span class="kicker">STORAGE UNIT · PAPER TEST PLATFORM</span><h2>Test 1 refrigerated container</h2><p>20 package channels · Type-T thermocouple readings · selected scope</p></div><span class="live"><i></i>${view.connection === 'connected' ? 'Live' : 'Offline'}</span></div><div class="package-grid">${view.packages.map((item, index) => `<button class="package ${statusClass(item.status)}" data-pod="${esc(item.name)}" title="Focus ${esc(item.name)} trend"><span class="index">${index + 1}</span><b>${esc(item.name)}</b><small>${temperature(item.temperatureC)}</small></button>`).join('')}</div><div class="legend"><span><i></i>In range</span><span><i class="cold"></i>Too cold</span><span><i class="warm"></i>Too warm</span><span><i class="unknown"></i>No reading</span></div></section><section class="panel chart-panel"><div class="panel-heading"><div><span class="kicker">TEMPERATURE TRENDS</span><h3>Thermal trajectory</h3><p>Temperature (°C) over time · safe range and target follow the selected profile.</p></div><span class="mono-label">${esc(state.filters.pod === 'all' ? 'ALL PODS' : state.filters.pod)}</span></div><div class="chart-wrap">${renderTrend(view.trendEvents, state.filters.pod)}</div></section><section class="panel"><div class="panel-heading"><div><span class="kicker">EVENT GENERATION COVERAGE</span><h3>Scenario coverage</h3><p>Counts come from persisted Pod events, not layout fixtures.</p></div><strong class="mono-label">${view.metrics.totalEvents.toLocaleString()} events</strong></div>${renderScenarioCoverage(view.scenarioCounts)}</section>${renderConfidence(view)}</div><aside class="panel"><div class="panel-heading"><div><span class="kicker">ATTENTION QUEUE</span><h3>Human review required</h3></div><span class="status ${view.attention.length ? 'warm' : 'good'}">${view.attention.length} active</span></div>${view.connection === 'offline' ? '<div class="empty"><strong>PostgreSQL is offline</strong>The attention queue will populate from persisted Pod excursions.</div>' : view.attention.length ? `<div class="attention-list">${view.attention.map((item) => `<div class="attention-item ${statusClass(item.status)}"><div class="row"><b>${esc(item.name)}</b><span class="status ${statusClass(item.status)}">${esc(statusLabel(item.status))}</span></div><div class="reading">${temperature(item.temperatureC)}<span>Scenario: ${esc(item.scenario || 'unknown')}</span></div><div class="actions"><button class="button small" data-ack="${esc(item.name)}">Acknowledge</button><button class="button small" data-pod="${esc(item.name)}">View trend</button></div></div>`).join('')}</div>` : '<div class="empty"><strong>No active Pod excursions</strong>Generate an outlier or failure scenario to exercise this queue.</div>'}</aside></div>`;
  }

  function rawCard(event) {
    const id = String(event.event_id);
    const open = state.expanded.has(id) ? ' open' : '';
    return `<details class="raw-card" data-payload="${esc(id)}"${open}><summary class="raw-summary"><span><span class="event-time">${esc(timestamp(event.timestamp))}</span><span class="event-title"> · ${esc(event.sensor_name)}</span></span><span class="temperature">${temperature(event.temperature_c)}</span><span class="raw-meta"><span>Profile <strong>${esc(event.vaccine_type)}</strong></span><span>Scenario <strong>${esc(event.scenario)}</strong></span><span>Event ID <strong>${esc(event.event_id)}</strong></span><span class="status ${statusClass(event.status)}">${esc(statusLabel(event.status))}</span><span>${esc(event.uncertainty_status || 'No uncertainty status')}</span></span></summary><pre class="payload">${esc(JSON.stringify(event, null, 2))}</pre></details>`;
  }

  function renderRawEvents() {
    adapter.setFilters(state.filters);
    const view = adapter.rawEventsView();
    return `<div class="page-header"><div><span class="eyebrow">READ-ONLY ENGINEERING AND AUDIT SURFACE</span><h1>Vaccine raw events</h1><p>Inspect exactly what the subscriber persisted. This page only reads and filters PostgreSQL results.</p></div><div class="page-actions"><button class="button" data-export>Export as CSV</button></div></div><div class="toolbar"><div class="toolbar-group"><span class="mono-label">SOURCE: POSTGRESQL</span></div>${filterControls(view.options)}<label class="follow"><input type="checkbox" data-follow ${state.follow ? 'checked' : ''}> Follow new events</label><span class="mono-label">${view.totalMatching.toLocaleString()} matching · newest first · 5 sec</span></div><div class="raw-list" id="rawList">${view.connection === 'offline' ? '<div class="panel empty"><strong>PostgreSQL is unavailable</strong>No event data is being changed. Reconnect the read-only bridge to continue.</div>' : view.events.length ? view.events.map(rawCard).join('') : '<div class="panel empty"><strong>No matching events</strong>Change the Pod or scenario filters to inspect another scope.</div>'}</div><div class="raw-footer"><span>Events <strong>${view.totalMatching.toLocaleString()}</strong></span><span>Source <strong>PostgreSQL</strong></span><span>Poll <strong>5 sec</strong></span>${view.truncated ? '<span>Showing newest 250</span>' : ''}</div>`;
  }

  function modelValue(result, kind) {
    if (!result || result.status === 'insufficient_data') return '—';
    if (kind === 'linear') return temperature(result.predictedTemperatureC);
    if (kind === 'logistic') return `${Math.round(result.excursionProbability * 100)}%`;
    return `${result.clusterCount} clusters`;
  }

  function modelCard(result, kind, title, description) {
    const status = result?.status || 'insufficient_data';
    return `<article class="model-card ${status}"><span class="kicker">${esc(result?.algorithm || kind)}</span><h2>${esc(title)}</h2><div class="model-value">${modelValue(result, kind)}</div><p>${esc(result?.message || 'Run analysis with more persisted events.')}</p><div class="model-meta"><span>Samples: ${result?.samples ?? '—'}</span><span>${result?.validation ? `${esc(result.validation.metric)}: ${result.validation.value}${result.validation.unit === '°C' ? '°C' : ''}` : 'Validation: —'}</span></div><p class="subtle">${esc(result?.basis || description)}</p></article>`;
  }

  function inferenceDraft(event) {
    return {
      pod: event?.sensor_name || 'Pod1',
      temperature: Number.isFinite(Number(event?.temperature_c)) ? Number(event.temperature_c) : -78.5,
      vaccine: event?.vaccine_type || 'pfizer_ultralow',
      scenario: event?.scenario || 'normal',
    };
  }

  function renderInferenceResult() {
    if (state.inferenceBusy) return '<div class="inference-message">Sending one Temperature event to the read-only ML service…</div>';
    if (state.inferenceError) return `<div class="inference-message error" role="alert">${esc(state.inferenceError)}</div>`;
    const result = state.inferenceResult;
    if (!result) return '<div class="inference-message">Fill in the small form and submit one event for an advisory result.</div>';
    const primary = result.primary || {};
    const probability = Number.isFinite(Number(primary.excursionProbability)) ? `${Math.round(Number(primary.excursionProbability) * 100)}%` : '—';
    const secondary = result.secondary || {};
    return `<div class="inference-result"><div class="inference-primary"><span class="kicker">PRIMARY · ${esc(primary.algorithm || 'logistic regression')}</span><strong>${esc(probability)}</strong><span>${esc(primary.prediction || primary.message || 'No prediction')}</span></div><div class="inference-secondary"><div><small>Temperature trend</small><b>${esc(secondary.linear?.predictedTemperatureC === undefined ? 'Not enough context' : temperature(secondary.linear.predictedTemperatureC))}</b></div><div><small>Pod group</small><b>${esc(secondary.clustering?.cluster ? `Cluster ${secondary.clustering.cluster}` : 'Not enough Pods')}</b></div><div><small>Validation</small><b>${esc(primary.validation ? `${primary.validation.metric}: ${primary.validation.value}` : '—')}</b></div></div><p class="subtle">${esc(primary.basis || 'CSV-trained educational model')} · results are advisory and read-only.</p></div>`;
  }

  function renderInferencePanel(view) {
    const latest = view.events.at(-1);
    if (!state.inferenceDraft) state.inferenceDraft = inferenceDraft(latest);
    const draft = state.inferenceDraft;
    const pods = [...new Set(['Pod1', ...view.events.map((event) => event.sensor_name)])].sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));
    const select = (name, options, value) => `<select class="field" data-inference-field="${name}">${options.map((option) => `<option value="${esc(option.value)}" ${option.value === value ? 'selected' : ''}>${esc(option.label)}</option>`).join('')}</select>`;
    return `<section class="panel inference-panel"><div class="panel-heading"><div><span class="kicker">ONE-EVENT INFERENCE</span><h3>Ask the ML service</h3><p>Enter the few facts that matter. The service derives status and keeps this read-only.</p></div><span class="mono-label">HTTP · PORT 5000</span></div><form data-inference-form class="inference-form"><label>Pod ${select('pod', pods.map((pod) => ({ value: pod, label: pod })), draft.pod)}</label><label>Temperature °C <input class="field" data-inference-field="temperature" type="number" step="0.1" value="${esc(draft.temperature)}"></label><label>Vaccine ${select('vaccine', [{ value: 'pfizer_ultralow', label: 'Pfizer ultralow' }, { value: 'moderna', label: 'Moderna' }], draft.vaccine)}</label><label>Scenario ${select('scenario', ['normal', 'warning', 'outlier', 'failure', 'recovery'].map((value) => ({ value, label: value })), draft.scenario)}</label><div class="inference-actions"><button class="button primary" type="submit">Predict event</button><button class="button" type="button" data-use-latest ${latest ? '' : 'disabled'}>Use latest event</button></div></form>${renderInferenceResult()}</section>`;
  }

  function renderInterpretation() {
    adapter.setFilters(state.filters);
    const view = adapter.analysisView();
    const currentKey = analysisKey(view);
    if (!state.analysis && view.connection === 'connected' && view.events.length) {
      state.analysis = adapter.runAnalysis(state.filters);
      state.analysisKey = currentKey;
      state.analysisAt = new Date().toISOString();
    }
    const models = state.analysis;
    const stale = Boolean(state.analysis && state.analysisKey !== currentKey);
    return `<div class="page-header"><div><span class="eyebrow">EXPLAINABLE ML-ASSISTED ANALYSIS</span><h1>Interpretation &amp; methodology</h1><p>Use three constrained algorithms to investigate temperature behavior. Model results assist review; raw status and human disposition remain authoritative.</p></div><div class="page-actions"><span class="connection-badge ${view.connection === 'connected' ? '' : 'offline'}"><i></i>${view.connection === 'connected' ? 'DATA AVAILABLE' : 'DATA UNAVAILABLE'}</span></div></div><div class="safety-note"><strong>Review boundary:</strong> ML results do not release, quarantine, or declare affected stock safe. Every result below identifies its data basis and validation state.</div>${renderInferencePanel(view)}<div class="model-toolbar">${filterControls(view.options)}<button class="button primary" data-run-analysis>Run analysis</button><span class="mono-label">${stale ? 'New event data available · run analysis to refresh' : state.analysis ? `Last run ${timestamp(state.analysisAt)}` : 'Initial analysis uses the selected scope'}</span></div><section class="model-grid">${modelCard(models?.linear, 'linear', 'Near-term temperature', 'Timestamped temperature readings')}${modelCard(models?.logistic, 'logistic', 'Excursion probability', 'Stored status labels and temperature offset')}${modelCard(models?.clustering, 'clustering', 'Pod behavior groups', 'Average, range, and excursion rate per Pod')}</section><section class="methodology"><span class="kicker">MODEL METHODOLOGY &amp; GOVERNANCE</span><h2>What each result means</h2><div class="methodology-grid"><div><h3>Linear regression</h3><p>Fits a line to timestamped temperatures and estimates the next observed direction. It is a trend aid, not a failure guarantee.</p></div><div><h3>Logistic regression</h3><p>Uses stored in-range and out-of-range labels to estimate excursion probability for the selected event scope.</p></div><div><h3>K-means clustering</h3><p>Groups Pods using average temperature, temperature range, and excursion rate so similar behavior can be investigated together.</p></div></div></section>`;
  }

  function bindCommon() {
    document.querySelectorAll('[data-filter]').forEach((control) => control.addEventListener('change', () => { state.filters[control.dataset.filter] = control.value; state.analysis = null; state.analysisKey = null; state.analysisAt = null; render(); }));
    document.querySelectorAll('[data-export]').forEach((button) => button.addEventListener('click', async () => { try { await bridge.exportAllEvents(); notify('CSV export prepared from PostgreSQL.'); } catch (error) { notify(error.message || 'CSV export is unavailable.'); } }));
    document.querySelectorAll('[data-route-link]').forEach((link) => link.classList.toggle('active', link.dataset.routeLink === state.route));
  }

  function bindOperations() {
    document.querySelectorAll('[data-pod]').forEach((button) => button.addEventListener('click', () => { state.filters.pod = button.dataset.pod; render(); }));
    document.querySelectorAll('[data-ack]').forEach((button) => button.addEventListener('click', () => { adapter.acknowledge(button.dataset.ack); notify(`${button.dataset.ack} acknowledged for this local prototype session.`); render(); }));
  }

  function bindRaw() {
    const follow = document.querySelector('[data-follow]');
    if (follow) follow.addEventListener('change', () => { state.follow = follow.checked; });
    document.querySelectorAll('[data-payload]').forEach((details) => details.addEventListener('toggle', () => { if (details.open) state.expanded.add(details.dataset.payload); else state.expanded.delete(details.dataset.payload); }));
  }

  function bindInterpretation() {
    const button = document.querySelector('[data-run-analysis]');
    if (button) button.addEventListener('click', () => { const view = adapter.analysisView(); state.analysis = adapter.runAnalysis(state.filters); state.analysisKey = analysisKey(view); state.analysisAt = new Date().toISOString(); notify('Analysis run completed for the selected event scope.'); render(); });
    const form = document.querySelector('[data-inference-form]');
    const latestButton = document.querySelector('[data-use-latest]');
    if (latestButton) latestButton.addEventListener('click', () => { state.inferenceDraft = inferenceDraft(adapter.analysisView().events.at(-1)); state.inferenceResult = null; state.inferenceError = null; render(); });
    if (form) form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const values = Object.fromEntries([...form.querySelectorAll('[data-inference-field]')].map((control) => [control.dataset.inferenceField, control.value]));
      try {
        const submitted = inference.buildInferenceEvent(values);
        const context = adapter.analysisView().events.slice(-20);
        state.inferenceDraft = values;
        state.inferenceBusy = true;
        state.inferenceResult = null;
        state.inferenceError = null;
        render();
        state.inferenceResult = await inference.requestPrediction({ event: submitted, contextEvents: context, baseUrl: global.ML_SERVICE_URL || inference.DEFAULT_BASE_URL });
      } catch (error) {
        state.inferenceError = error.message || 'Inference request failed.';
      } finally {
        state.inferenceBusy = false;
        render();
      }
    });
  }

  function render() {
    state.route = (global.location.hash.slice(1) || 'operations').toLowerCase();
    if (!['operations', 'raw-events', 'interpretation'].includes(state.route)) state.route = 'operations';
    app.innerHTML = state.route === 'operations' ? renderOperations() : state.route === 'raw-events' ? renderRawEvents() : renderInterpretation();
    setConnection(adapter.operationsView().connection);
    bindCommon();
    if (state.route === 'operations') bindOperations();
    if (state.route === 'raw-events') bindRaw();
    if (state.route === 'interpretation') bindInterpretation();
  }

  global.addEventListener('hashchange', () => {
    const nextRoute = (global.location.hash.slice(1) || 'operations').toLowerCase();
    if (nextRoute === 'interpretation' && state.route !== 'interpretation') { state.analysis = null; state.analysisKey = null; }
    render();
  });
  render();
  bridge.watchDatabase((rawEvents) => {
    const latest = rawEvents.at(-1);
    const latestId = latest ? String(latest.event_id || latest.timestamp) : null;
    const shouldFollow = state.route === 'raw-events' && state.follow && state.lastEventId && latestId !== state.lastEventId;
    state.lastEventId = latestId;
    adapter.setEvents(rawEvents);
    render();
    if (shouldFollow) global.scrollTo({ top: 0, behavior: 'smooth' });
  }, () => { state.lastEventId = null; adapter.setOffline(); render(); });
})(typeof globalThis === 'undefined' ? this : globalThis);
