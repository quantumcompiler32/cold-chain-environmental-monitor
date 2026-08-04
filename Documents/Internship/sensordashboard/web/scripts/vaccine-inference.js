(function exposeVaccineInference(root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.VaccineInference = factory(root.fetch.bind(root));
})(typeof globalThis === 'undefined' ? this : globalThis, function vaccineInferenceFactory(defaultFetch) {
  const DEFAULT_BASE_URL = 'http://127.0.0.1:5000';

  function buildInferenceEvent(values) {
    const temperature = Number(values.temperature);
    if (!values.pod) throw new Error('Choose a Pod.');
    if (!Number.isFinite(temperature)) throw new Error('Enter a temperature in °C.');
    return {
      sensor_name: String(values.pod),
      temperature_c: temperature,
      vaccine_type: String(values.vaccine || 'pfizer_ultralow'),
      scenario: String(values.scenario || 'normal'),
    };
  }

  async function requestPrediction({ event, contextEvents = [], fetchImpl = defaultFetch, baseUrl = DEFAULT_BASE_URL }) {
    const response = await fetchImpl(`${baseUrl}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event, context_events: contextEvents }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Inference service returned ${response.status}`);
    return payload;
  }

  return { DEFAULT_BASE_URL, buildInferenceEvent, requestPrediction };
});
