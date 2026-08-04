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

  function setStatus(message, kind = '') {
    status.textContent = message;
    status.className = `scope-pill ${kind}`.trim();
  }

  function setFeedback(message, kind = '') {
    feedback.textContent = message;
    feedback.className = `inference-feedback ${kind}`.trim();
  }

  function renderResult(payload) {
    const primary = payload.primary || {};
    const linear = payload.secondary?.linear || {};
    const clustering = payload.secondary?.clustering || {};
    const probability = Number.isFinite(Number(primary.excursionProbability))
      ? `${Math.round(Number(primary.excursionProbability) * 100)}%`
      : 'Not available';
    const validation = primary.validation
      ? `${primary.validation.metric}: ${primary.validation.value}`
      : 'Not available';
    result.innerHTML = `<div class="inference-primary"><span class="kicker">PRIMARY · ${esc(primary.algorithm || 'logistic regression')}</span><strong>${esc(probability)}</strong><span>${esc(primary.prediction || primary.message || 'No prediction')}</span></div><div class="inference-secondary"><div><small>Temperature trend</small><b>${esc(linear.predictedTemperatureC === undefined ? linear.message || 'Not enough context' : formatTemperature(linear.predictedTemperatureC))}</b></div><div><small>Pod group</small><b>${esc(clustering.cluster === undefined ? clustering.message || 'Not enough Pods' : `Cluster ${clustering.cluster} of ${clustering.clusterCount}`)}</b></div><div><small>Validation</small><b>${esc(validation)}</b></div></div><p class="subtle">${esc(primary.basis || 'CSV-trained educational model')} · model ${esc(payload.model_version || 'unknown')} · results are advisory and read-only.</p>`;
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
      renderResult(payload);
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
