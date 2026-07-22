(function initVaccineLiveRunner(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  const ALL_PODS = Array.from({ length: 20 }, (_, index) => `Pod${index + 1}`);
  const DEFAULT_PODS = ['Pod1', 'Pod2', 'Pod3', 'Pod6', 'Pod11', 'Pod20'];
  const DEFAULT_MAX_EVENTS = 20;
  let selectedPods = DEFAULT_PODS.slice();
  let profile = data.getProfile('pfizer_ultralow');
  let bridgeOnline = false;
  let running = false;
  let toastTimer;

  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const formatC = (value) => `${Number(value).toFixed(1)}°C`;

  function showToast(message) {
    $('toast').textContent = message;
    $('toast').classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2600);
  }

  function setBridgeState(online, message) {
    bridgeOnline = online;
    const status = $('bridgeStatus');
    status.classList.toggle('online', online);
    status.classList.toggle('offline', !online);
    status.innerHTML = `<i></i>${esc(message || (online ? 'Bridge connected' : 'Bridge offline'))}`;
    updateButtons();
  }

  function renderProfile() {
    $('profileName').textContent = profile.label;
    $('profileTarget').textContent = formatC(profile.targetC);
    $('profileRange').textContent = `${formatC(profile.lowerLimitC)} to ${formatC(profile.upperLimitC)}`;
    $('profileSourceText').textContent = profile.guidance || 'Statuses are calculated from the selected profile.';
    $('profileSourceLink').href = profile.sourceUrl || '#';
    $('profileSourceLink').style.display = profile.sourceUrl ? 'inline' : 'none';
    $('runMinTemp').value = profile.lowerLimitC;
    $('runMaxTemp').value = profile.upperLimitC;
    $('profileGuidance').textContent = profile.guidance || 'Statuses are calculated from the selected profile.';
  }

  function renderPods() {
    $('runPodPicker').innerHTML = ALL_PODS.map((pod) => `<button type="button" class="run-pod${selectedPods.includes(pod) ? ' selected' : ''}" aria-pressed="${selectedPods.includes(pod)}" data-run-pod="${pod}">${pod}</button>`).join('');
    $('runPodPicker').querySelectorAll('[data-run-pod]').forEach((button) => button.addEventListener('click', () => {
      const pod = button.dataset.runPod;
      selectedPods = selectedPods.includes(pod) ? selectedPods.filter((item) => item !== pod) : [...selectedPods, pod];
      renderPods();
      updateButtons();
    }));
  }

  function formError() {
    if (!selectedPods.length) return 'Select at least one Pod.';
    if (!Number.isInteger(Number($('runInterval').value)) || Number($('runInterval').value) < 50) return 'Interval must be at least 50 ms.';
    const min = Number($('runMinTemp').value);
    const max = Number($('runMaxTemp').value);
    if (!Number.isFinite(min) || !Number.isFinite(max)) return 'Enter both temperature bounds.';
    if (min >= max) return 'Minimum temperature must be lower than maximum temperature.';
    return '';
  }

  function updateButtons() {
    const error = formError();
    $('startRunButton').disabled = !bridgeOnline || Boolean(error) || running;
    $('stopRunButton').disabled = !running;
    if (!running && error) $('runProgress').textContent = error;
  }

  function syncProfile() {
    profile = data.getProfile($('runProfile').value);
    renderProfile();
    updateButtons();
  }

  function updateStatus(status) {
    running = Boolean(status.running);
    $('runProgress').textContent = status.message || (running ? 'Run in progress…' : 'Ready to run.');
    updateButtons();
  }

  async function startRun() {
    const error = formError();
    if (error) return showToast(error);
    running = true;
    updateButtons();
    $('runProgress').textContent = `Starting ${selectedPods.length} Pods…`;
    try {
      const result = await bridge.request('/api/run/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        profile: profile.id,
        scenario: $('runScenario').value,
        sensors: selectedPods,
        interval_ms: Number($('runInterval').value),
        max_events: DEFAULT_MAX_EVENTS,
        save_to_database: $('saveToDatabase').checked,
        min_temp: Number($('runMinTemp').value),
        max_temp: Number($('runMaxTemp').value),
      }) });
      updateStatus(result);
      showToast('Live run started.');
    } catch (error) {
      running = false;
      updateButtons();
      showToast(error.message);
    }
  }

  async function stopRun() {
    try { updateStatus(await bridge.request('/api/run/stop', { method: 'POST' })); } catch (error) { showToast(error.message); }
  }

  $('runProfile').addEventListener('change', syncProfile);
  $('runInterval').addEventListener('input', updateButtons);
  $('runMinTemp').addEventListener('input', updateButtons);
  $('runMaxTemp').addEventListener('input', updateButtons);
  $('selectAllPods').addEventListener('click', () => { selectedPods = ALL_PODS.slice(); renderPods(); updateButtons(); });
  $('clearPods').addEventListener('click', () => { selectedPods = []; renderPods(); updateButtons(); });
  $('startRunButton').addEventListener('click', startRun);
  $('stopRunButton').addEventListener('click', stopRun);

  renderPods();
  renderProfile();
  const observer = bridge.createObserver({
    onHealth: (health) => setBridgeState(Boolean(health.mqtt_connected), health.mqtt_connected ? 'Bridge connected' : 'Bridge online · MQTT offline'),
    onStatus: updateStatus,
  });
  observer.start();
})(typeof globalThis === 'undefined' ? this : globalThis);
