(function initVaccineLiveRunner(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  const ALL_PODS = Array.from({ length: 20 }, (_, index) => `Pod${index + 1}`);
  const DEFAULT_PODS = ['Pod1', 'Pod2', 'Pod3', 'Pod6', 'Pod11', 'Pod20'];
  const DEFAULT_MAX_EVENTS = 20;
  const SCENARIO_HELP = {
    normal: 'Replays the source pattern without injecting an excursion.',
    outlier: 'Adds an intentional threshold breach on every twentieth event.',
    failure: 'Holds every event above the selected maximum to model sustained protection loss.',
    recovery: 'Starts above the selected maximum and moves toward the profile target across the run.',
  };
  let selectedPods = DEFAULT_PODS.slice();
  let profile = data.getProfile('pfizer_ultralow');
  let bridgeOnline = false;
  let running = false;
  let sourceFileId = null;
  let sourceFileName = null;
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
    const usesCustomBounds = profile.id === 'moderna';
    $('profileName').textContent = profile.label;
    $('profileTarget').textContent = formatC(profile.targetC);
    $('profileRange').textContent = `${formatC(profile.lowerLimitC)} to ${formatC(profile.upperLimitC)}`;
    $('profileSourceText').textContent = profile.guidance || 'Statuses are calculated from the selected profile.';
    $('profileSourceLink').href = profile.sourceUrl || '#';
    $('profileSourceLink').style.display = profile.sourceUrl ? 'inline' : 'none';
    $('customBoundsFields').hidden = !usesCustomBounds;
    $('runMinTemp').disabled = !usesCustomBounds;
    $('runMaxTemp').disabled = !usesCustomBounds;
    $('runMinTemp').value = usesCustomBounds ? profile.lowerLimitC : '';
    $('runMaxTemp').value = usesCustomBounds ? profile.upperLimitC : '';
    $('profileGuidance').textContent = usesCustomBounds
      ? `${profile.guidance} These suggested bounds are editable for this simulation.`
      : 'Pfizer ultralow uses its fixed simulation range. Select Moderna / Spikevax to show editable suggested bounds.';
    renderScenarioHelp();
  }

  function renderScenarioHelp() {
    const selected = selectedScenarios();
    $('scenarioGuidance').textContent = selected.length
      ? selected.map((scenario) => SCENARIO_HELP[scenario]).join(' ')
      : 'Select at least one scenario.';
    const count = Number($('runEventCount').value) || DEFAULT_MAX_EVENTS;
    $('runSizeSummary').textContent = `${count} events × ${selected.length || 0} scenario${selected.length === 1 ? '' : 's'} / selected Pod`;
  }

  function selectedScenarios() {
    return Array.from(document.querySelectorAll('input[name="runScenario"]:checked')).map((input) => input.value);
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
    if (!selectedScenarios().length) return 'Select at least one scenario.';
    if (!Number.isInteger(Number($('runEventCount').value)) || Number($('runEventCount').value) < 1 || Number($('runEventCount').value) > 5000) return 'Events per scenario must be between 1 and 5000.';
    if (profile.id !== 'moderna') return '';
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
        scenarios: selectedScenarios(),
        scenario: selectedScenarios()[0],
        sensors: selectedPods,
        interval_ms: Number($('runInterval').value),
        max_events: Number($('runEventCount').value),
        save_to_database: $('saveToDatabase').checked,
        source_file_id: sourceFileId,
        source_file_name: sourceFileName,
        min_temp: profile.id === 'moderna' ? Number($('runMinTemp').value) : null,
        max_temp: profile.id === 'moderna' ? Number($('runMaxTemp').value) : null,
      }) });
      updateStatus(result);
      showToast('Live run started.');
    } catch (error) {
      running = false;
      if (error.message.includes('CSV upload')) {
        sourceFileId = null;
        sourceFileName = null;
        $('csvSourceStatus').textContent = 'Using the bundled local experiment';
      }
      updateButtons();
      showToast(error.message);
    }
  }

  async function uploadSource() {
    const file = $('csvSourceInput').files[0];
    if (!file) return showToast('Choose a CSV file first.');
    if (!bridgeOnline) return showToast('Connect the bridge before uploading a CSV.');
    $('uploadSourceButton').disabled = true;
    $('csvSourceStatus').textContent = `Uploading ${file.name}…`;
    try {
      const result = await bridge.request('/api/run/source', { method: 'POST', headers: { 'Content-Type': 'text/csv', 'X-Filename': file.name }, body: file });
      sourceFileId = result.source_file_id;
      sourceFileName = result.filename;
      $('csvSourceStatus').textContent = `${result.filename} ready (${Number(result.bytes).toLocaleString()} bytes)`;
      showToast('CSV ready for the next run.');
    } catch (error) {
      sourceFileId = null;
      sourceFileName = null;
      $('csvSourceStatus').textContent = 'Using the bundled local experiment';
      showToast(error.message);
    } finally {
      $('uploadSourceButton').disabled = false;
    }
  }

  async function stopRun() {
    try { updateStatus(await bridge.request('/api/run/stop', { method: 'POST' })); } catch (error) { showToast(error.message); }
  }

  $('runProfile').addEventListener('change', syncProfile);
  document.querySelectorAll('input[name="runScenario"]').forEach((input) => input.addEventListener('change', () => { renderScenarioHelp(); updateButtons(); }));
  $('runInterval').addEventListener('input', updateButtons);
  $('runEventCount').addEventListener('input', () => { renderScenarioHelp(); updateButtons(); });
  $('runMinTemp').addEventListener('input', updateButtons);
  $('runMaxTemp').addEventListener('input', updateButtons);
  $('selectAllPods').addEventListener('click', () => { selectedPods = ALL_PODS.slice(); renderPods(); updateButtons(); });
  $('clearPods').addEventListener('click', () => { selectedPods = []; renderPods(); updateButtons(); });
  $('startRunButton').addEventListener('click', startRun);
  $('stopRunButton').addEventListener('click', stopRun);
  $('uploadSourceButton').addEventListener('click', uploadSource);

  renderPods();
  renderProfile();
  renderScenarioHelp();
  const observer = bridge.createObserver({
    onHealth: (health) => setBridgeState(Boolean(health.mqtt_connected), health.mqtt_connected ? 'Bridge connected' : 'Bridge online · MQTT offline'),
    onStatus: updateStatus,
  });
  observer.start();
})(typeof globalThis === 'undefined' ? this : globalThis);
