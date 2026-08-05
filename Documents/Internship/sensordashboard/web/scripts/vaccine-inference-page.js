/* Purpose: wire the inference form to the optional advisory read-only service. */
(function initVaccineInferencePage(global) {
  const inference = global.VaccineInference;
  const bridge = global.VaccineBridge;
  if (!inference || !bridge) return;

  const form = document.getElementById('inferenceForm');
  const status = document.getElementById('inferenceServiceStatus');
  const feedback = document.getElementById('inferenceFeedback');
  const result = document.getElementById('inferenceResult');
  const latestButton = document.getElementById('useLatestInference');
  const podField = document.getElementById('inferencePod');
  const temperatureField = document.getElementById('inferenceTemperature');
  const vaccineField = document.getElementById('inferenceVaccine');
  const scenarioField = document.getElementById('inferenceScenario');
  const baseUrl = global.ML_SERVICE_URL || inference.DEFAULT_BASE_URL;
  const state = { events: [], busy: false };

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const formatTemperature = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}°C` : 'Not available';
  const formatNumber = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : 'Not available';

  function setStatus(message, kind = '') {
    status.textContent = message;
    status.className = `scope-pill ${kind}`.trim();
  }

  function setFeedback(message, kind = '') {
    feedback.textContent = message;
    feedback.className = `inference-feedback ${kind}`.trim();
  }

  function explainPrediction(payload, submitted) {
    const primary = payload.primary || {};
    const input = payload.input || submitted || {};
    const probability = Number(primary.excursionProbability);
    const temperature = Number(input.temperature_c);
    const lower = Number(input.storage_min_c);
    const upper = Number(input.storage_max_c);
    const range = Number.isFinite(lower) && Number.isFinite(upper) ? `${formatTemperature(lower)} to ${formatTemperature(upper)}` : 'the stored vaccine range';
    const temperatureNote = Number.isFinite(temperature) && Number.isFinite(lower) && Number.isFinite(upper)
      ? temperature < lower ? `The reading is below the stored range (${range}).`
        : temperature > upper ? `The reading is above the stored range (${range}).`
          : `The reading itself is inside the stored range (${range}).`
      : 'The stored range could not be shown for this event.';
    const modelNote = Number.isFinite(probability)
      ? `The logistic model estimates a ${Math.round(probability * 100)}% likelihood of an investigation-needed pattern.`
      : 'The logistic model could not produce a probability for this event.';
    const decisionNote = primary.prediction === 'investigation-needed'
      ? 'That makes this a review signal, not an automatic disposition.'
      : 'That supports a stable-pattern reading, but it is still advisory.';
    return `For ${input.sensor_name || 'this Pod'}, ${modelNote} ${temperatureNote} ${decisionNote}`;
  }

  function eventTime(event, fallback) {
    const parsed = Date.parse(String(event?.event_time || event?.timestamp || ''));
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function renderPredictionChart(payload, submitted) {
    const input = payload.input || submitted || {};
    const linear = payload.secondary?.linear || {};
    const samePod = state.events.filter((event) => event.sensor_name === input.sensor_name);
    const source = (samePod.length ? samePod : state.events).slice(-12);
    const context = source
      .map((event, index) => ({ value: Number(event.temperature_c), time: eventTime(event, index), kind: 'context' }))
      .filter((point) => Number.isFinite(point.value));
    const submittedPoint = { value: Number(input.temperature_c), time: Date.now(), kind: 'submitted' };
    const observed = [...context, submittedPoint].sort((left, right) => left.time - right.time);
    const forecastValue = Number(linear.predictedTemperatureC);
    const forecast = Number.isFinite(forecastValue) ? { value: forecastValue, time: observed.at(-1).time + 1, kind: 'forecast' } : null;
    const points = forecast ? [...observed, forecast] : observed;
    const values = points.map((point) => point.value).filter(Number.isFinite);
    if (!values.length) return '<div class="inference-chart-empty">No temperature points were available to draw.</div>';

    const width = 760;
    const height = 230;
    const margin = { top: 18, right: 16, bottom: 28, left: 48 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const lower = Number(input.storage_min_c);
    const upper = Number(input.storage_max_c);
    const target = Number(input.target_c);
    const bounds = [...values, lower, upper, target].filter(Number.isFinite);
    const rawMin = Math.min(...bounds);
    const rawMax = Math.max(...bounds);
    const padding = Math.max(1, (rawMax - rawMin) * 0.12);
    const min = rawMin - padding;
    const max = rawMax + padding;
    const x = (index) => margin.left + (points.length <= 1 ? plotWidth / 2 : index * plotWidth / (points.length - 1));
    const y = (value) => margin.top + (max - value) * plotHeight / (max - min);
    const observedCount = observed.length;
    const observedPath = observed.map((point, index) => `${index ? 'L' : 'M'}${x(index).toFixed(1)},${y(point.value).toFixed(1)}`).join(' ');
    const forecastPath = forecast && observedCount ? `M${x(observedCount - 1).toFixed(1)},${y(observed.at(-1).value).toFixed(1)} L${x(points.length - 1).toFixed(1)},${y(forecast.value).toFixed(1)}` : '';
    const safeBand = Number.isFinite(lower) && Number.isFinite(upper)
      ? `<rect x="${margin.left}" y="${y(upper).toFixed(1)}" width="${plotWidth}" height="${Math.max(0, y(lower) - y(upper)).toFixed(1)}" fill="rgba(16,185,129,.08)"/>`
      : '';
    const thresholdLines = [
      [upper, '#ef4444', 'upper limit'],
      [target, '#fbbf24', 'target'],
      [lower, '#60a5fa', 'lower limit'],
    ].filter(([value]) => Number.isFinite(value) && value >= min && value <= max)
      .map(([value, color, label]) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(value).toFixed(1)}" y2="${y(value).toFixed(1)}" stroke="${color}" stroke-dasharray="${label === 'target' ? '2 4' : '4 4'}" opacity=".72"/><text x="${width - margin.right}" y="${(y(value) - 4).toFixed(1)}" text-anchor="end" fill="${color}" font-size="9">${label}</text>`).join('');
    const grid = [min, (min + max) / 2, max].map((value) => `<line x1="${margin.left}" x2="${width - margin.right}" y1="${y(value).toFixed(1)}" y2="${y(value).toFixed(1)}" stroke="rgba(255,255,255,.08)"/><text x="${margin.left - 7}" y="${(y(value) + 3).toFixed(1)}" text-anchor="end" fill="#6b7280" font-size="9">${value.toFixed(1)}°</text>`).join('');
    const dots = observed.map((point, index) => `<circle cx="${x(index).toFixed(1)}" cy="${y(point.value).toFixed(1)}" r="${point.kind === 'submitted' ? 5 : 3}" fill="${point.kind === 'submitted' ? '#f9a8d4' : '#c4b5fd'}"/>`).join('');
    const forecastDot = forecast ? `<circle cx="${x(points.length - 1).toFixed(1)}" cy="${y(forecast.value).toFixed(1)}" r="5" fill="#fbbf24"/>` : '';
    const contextLabel = samePod.length ? `${input.sensor_name} context` : 'Recent context';
    return `<div class="inference-chart-heading"><div><strong>Temperature context and projection</strong><span>${esc(contextLabel)} · submitted point · optional trend estimate</span></div><span>${forecast ? `Projection ${formatTemperature(forecast.value)}` : 'No projection yet'}</span></div><svg class="inference-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Temperature context and model projection">${safeBand}${grid}${thresholdLines}<path d="${observedPath}" fill="none" stroke="#c4b5fd" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>${forecastPath ? `<path d="${forecastPath}" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="5 4"/>` : ''}${dots}${forecastDot}</svg><div class="inference-chart-legend"><span><i class="context"></i>Context</span><span><i class="submitted"></i>Submitted event</span>${forecast ? '<span><i class="forecast"></i>Trend estimate</span>' : ''}</div>`;
  }

  function renderResult(payload, submitted) {
    const primary = payload.primary || {};
    const linear = payload.secondary?.linear || {};
    const clustering = payload.secondary?.clustering || {};
    const input = payload.input || submitted || {};
    const features = payload.features || {};
    const probability = Number.isFinite(Number(primary.excursionProbability))
      ? `${Math.round(Number(primary.excursionProbability) * 100)}%`
      : 'Not available';
    const probabilityWidth = Math.max(0, Math.min(100, Math.round(Number(primary.excursionProbability) * 100) || 0));
    const validation = primary.validation
      ? `${primary.validation.metric}: ${formatNumber(primary.validation.value, 3)}${primary.validation.unit ? ` ${primary.validation.unit}` : ''}`
      : 'Not available';
    result.innerHTML = `<div class="inference-primary"><span class="kicker">PRIMARY · ${esc(primary.algorithm || 'logistic regression')}</span><strong>${esc(probability)}</strong><span>${esc(primary.prediction || primary.message || 'No prediction')}</span><div class="probability-meter" aria-label="Investigation probability ${esc(probability)}"><i style="width:${probabilityWidth}%"></i></div><small>0% <span>50% review threshold</span> 100%</small></div><div class="inference-explanation"><span class="kicker">WHAT THE INFERENCE MADE</span><p>${esc(explainPrediction(payload, submitted))}</p><div class="inference-feature-list"><div><small>Temperature used</small><b>${esc(formatTemperature(input.temperature_c))}</b></div><div><small>Elapsed context</small><b>${esc(formatNumber(features.hours, 2))} hours</b></div><div><small>Sensor spread</small><b>${esc(formatTemperature(features.sensor_spread_c))}</b></div></div></div><div class="inference-chart-card">${renderPredictionChart(payload, submitted)}</div><div class="inference-secondary"><div><small>Temperature trend</small><b>${esc(linear.predictedTemperatureC === undefined ? linear.message || 'Not enough context' : formatTemperature(linear.predictedTemperatureC))}</b><span>${linear.slopeCPerHour === undefined ? 'Add context for a projection' : `${formatNumber(linear.slopeCPerHour, 3)}°C/hour from saved model`}</span></div><div><small>Pod group</small><b>${esc(clustering.cluster === undefined ? clustering.message || 'Not enough Pods' : `Cluster ${clustering.cluster} of ${clustering.clusterCount}`)}</b><span>${clustering.status === 'insufficient_data' ? 'Use three or more Pods' : 'Behavior group from saved model'}</span></div><div><small>Validation</small><b>${esc(validation)}</b><span>Model check from the saved training bundle</span></div></div><p class="subtle">${esc(primary.basis || 'CSV-trained educational model')} · model ${esc(payload.model_version || 'unknown')} · results are advisory and read-only.</p>`;
    result.hidden = false;
  }

  function useLatestEvent() {
    const latest = state.events.at(-1);
    if (!latest) return;
    podField.value = latest.sensor_name || 'Pod1';
    temperatureField.value = Number.isFinite(Number(latest.temperature_c)) ? latest.temperature_c : '';
    vaccineField.value = latest.vaccine_type || 'pfizer_ultralow';
    scenarioField.value = latest.scenario || 'normal';
    setFeedback('Loaded the latest persisted event. Review it, then submit when ready.');
  }

  async function checkService() {
    try {
      const response = await fetch(`${baseUrl}/health`, { cache: 'no-store' });
      const payload = await response.json();
      if (payload.ready) setStatus(`MODEL READY · ${payload.model_version || 'saved bundle'}`, 'ready');
      else setStatus('MODEL NEEDS TRAINING', 'warning');
    } catch (error) {
      setStatus('ML SERVICE OFFLINE', 'offline');
    }
  }

  async function submitInference(event) {
    event.preventDefault();
    if (state.busy) return;
    state.busy = true;
    result.hidden = true;
    setFeedback('Sending one Temperature event to the read-only ML service…');
    try {
      const submitted = inference.buildInferenceEvent({
        pod: podField.value,
        temperature: temperatureField.value,
        vaccine: vaccineField.value,
        scenario: scenarioField.value,
      });
      const payload = await inference.requestPrediction({
        event: submitted,
        contextEvents: state.events.slice(-20),
        baseUrl,
      });
      renderResult(payload, submitted);
      setFeedback('Prediction received. Operational status and stock disposition remain unchanged.', 'success');
    } catch (error) {
      setFeedback(error.message || 'Inference request failed.', 'error');
    } finally {
      state.busy = false;
    }
  }

  form.addEventListener('submit', submitInference);
  latestButton.addEventListener('click', useLatestEvent);
  bridge.watchDatabase((events) => {
    state.events = events || [];
    latestButton.disabled = !state.events.length;
  }, () => {
    state.events = [];
    latestButton.disabled = true;
  });
  checkService();
})(typeof globalThis === 'undefined' ? this : globalThis);
