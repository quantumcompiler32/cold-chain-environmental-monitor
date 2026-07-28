/*
 * THROWAWAY UI PROTOTYPE — question: which analytics layout helps an operator
 * turn a temperature event stream into a safe, auditable next action?
 * Three variants on domain-vaccine.html?variant=A|B|C. State is in memory only.
 */
(function vaccineAnalyticsPrototype(global) {
  const data = global.VaccineData;
  const bridge = global.VaccineBridge;
  if (!data || !bridge) return;

  const keys = ['A', 'B', 'C'];
  const names = { A: 'Operations queue', B: 'Excursion casefile', C: 'Fleet reliability' };
  const query = new URLSearchParams(global.location.search);
  let variant = String(query.get('variant') || '').toUpperCase();
  if (!keys.includes(variant)) return;

  const target = document.getElementById('analyticsPrototype');
  let events = [];
  let workflow = { acknowledgement: 'Unacknowledged', review: 'Not started', note: 'No note', disposition: 'Pending qualified review' };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const c = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(1) + '°C' : '—';
  const time = (value) => { const d = new Date(value); return Number.isNaN(d) ? 'Unknown time' : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); };
  const isBreach = (event) => event.status === 'TOO_COLD' || event.status === 'TOO_WARM';

  function model() {
    const latest = data.summarizeSensors(events);
    const breaches = latest.filter((item) => item.status === 'TOO_COLD' || item.status === 'TOO_WARM');
    const focus = breaches[0] || latest[0] || { sensorName: 'Pod 03', latestTemperatureC: -58.1, status: 'TOO_WARM', latestScenario: 'failure', readingCount: 28 };
    const incidentEvents = events.filter((event) => event.sensor_name === focus.sensorName).slice(-18);
    const temperatures = incidentEvents.map((event) => Number(event.temperature_c)).filter(Number.isFinite);
    const min = temperatures.length ? Math.min(...temperatures) : -79.1;
    const max = temperatures.length ? Math.max(...temperatures) : -58.1;
    const related = events.filter(isBreach).slice(-30);
    return { latest, breaches, focus, incidentEvents, min, max, related, total: events.length };
  }

  function incidentCard(item, index) {
    const warm = item.status === 'TOO_WARM';
    return `<article class="proto-incident ${warm ? 'warm' : 'cold'}"><div class="proto-incident-top"><span class="proto-severity">${warm ? 'Critical' : 'Warning'}</span><span>${index === 0 ? 'Active now' : 'Awaiting review'}</span></div><strong>${esc(item.sensorName)}</strong><div class="proto-temp">${c(item.latestTemperatureC)} <small>${warm ? 'above' : 'below'} range</small></div><p>${esc(item.latestScenario || 'Unknown cause')} · ${item.readingCount} persisted readings</p><button type="button" data-action="ack">Acknowledge</button></article>`;
  }

  function bars(items) {
    const values = items.map((event) => Number(event.temperature_c)).filter(Number.isFinite);
    const low = Math.min(...values, -82); const high = Math.max(...values, -55); const span = Math.max(high - low, 1);
    return `<div class="proto-bars">${values.map((value) => `<i title="${c(value)}" style="height:${18 + ((value - low) / span) * 74}%"></i>`).join('')}</div>`;
  }

  function variantA(m) {
    return `<div class="proto-header"><div><span class="proto-kicker">PROTOTYPE A · OPERATIONS COMMAND</span><h2>Act on the risks that need a human now.</h2><p>Each alert is a sustained simulated breach, not a single noisy reading. Stock disposition remains a qualified operator decision.</p></div><div class="proto-status"><b>${m.breaches.length}</b><span>active incident${m.breaches.length === 1 ? '' : 's'}</span></div></div><div class="proto-command-grid"><section class="proto-panel"><h3>Active incidents</h3><div class="proto-incident-list">${m.breaches.length ? m.breaches.map(incidentCard).join('') : '<div class="proto-empty">No active excursions in the latest sensor state.</div>'}</div></section><section class="proto-panel proto-focus"><div class="proto-panel-heading"><div><span>Incident INC-2026-031</span><h3>${esc(m.focus.sensorName)} temperature excursion</h3></div><span class="condition ${String(m.focus.status).toLowerCase().replace('_', '-')}">${esc(m.focus.status).replace('_', ' ')}</span></div><div class="proto-metrics"><div><b>${c(m.focus.latestTemperatureC)}</b><span>current temperature</span></div><div><b>${c(m.min)}–${c(m.max)}</b><span>observed range</span></div><div><b>18 min</b><span>outside range</span></div></div>${bars(m.incidentEvents)}<div class="proto-actions"><button type="button" data-action="ack">Acknowledge</button><button type="button" data-action="review">Start stock review</button><button type="button" data-action="note">Add note</button></div></section><section class="proto-panel"><h3>Affected stock review</h3><div class="proto-stock"><b>Batch ULT-4821</b><span>Ultra-low vaccine · 240 doses</span><span>Exposure: 18 min · ${c(m.min)} to ${c(m.max)}</span><em>${workflow.disposition}</em></div><p class="proto-safety">Simulation only — this dashboard does not determine whether stock is safe or eligible for release.</p><button type="button" data-action="review">Open qualified review</button></section></div>${workflowView()}`;
  }

  function variantB(m) {
    const steps = ['Normal', 'Breach detected', 'Alert sent', 'Operator acknowledged', 'Temperature recovered', 'Stock reviewed'];
    return `<div class="proto-header proto-case-header"><div><span class="proto-kicker">PROTOTYPE B · EXCURSION CASEFILE</span><h2>Tell the story of one excursion from detection to disposition.</h2><p>Designed for reviewing the evidence behind an incident, rather than scanning the whole fleet.</p></div><span class="proto-case-id">INC-2026-031 · ${esc(m.focus.sensorName)}</span></div><div class="proto-case-layout"><section class="proto-panel proto-case-main"><div class="proto-panel-heading"><div><h3>Temperature evidence</h3><span>${time(m.incidentEvents[0]?.timestamp)} → ${time(m.incidentEvents.at(-1)?.timestamp)}</span></div><b class="proto-current">${c(m.focus.latestTemperatureC)}</b></div>${bars(m.incidentEvents)}<div class="proto-evidence-row"><div><b>Range reached</b><span>${c(m.min)} to ${c(m.max)}</span></div><div><b>Sensor confidence</b><span>±0.5°C simulation accuracy</span></div><div><b>Likely cause</b><span>Unknown · operator input required</span></div></div></section><aside class="proto-panel proto-timeline"><h3>Excursion timeline</h3>${steps.map((step, i) => `<div class="proto-step ${i < 3 || (i === 3 && workflow.acknowledgement !== 'Unacknowledged') ? 'done' : ''}"><i></i><div><b>${step}</b><span>${i === 0 ? 'Prior readings in range' : i === 1 ? time(m.incidentEvents[0]?.timestamp) : i === 2 ? 'Sustained breach threshold reached' : i === 3 ? workflow.acknowledgement : 'Pending operator workflow'}</span></div></div>`).join('')}</aside></div><section class="proto-panel proto-decision"><div><span class="proto-kicker">REVIEW GATE</span><h3>Stock decision stays with a qualified reviewer</h3><p>Batch ULT-4821 · 240 doses · simulated exposure window 18 minutes.</p></div><div class="proto-actions"><button type="button" data-action="ack">Acknowledge alert</button><button type="button" data-action="review">Start review</button><button type="button" data-action="resolve">Mark temperature recovered</button></div></section>${workflowView()}`;
  }

  function variantC(m) {
    const statusCounts = m.latest.reduce((all, item) => { all[item.status] = (all[item.status] || 0) + 1; return all; }, {});
    const rows = m.latest.slice(0, 8).map((item) => `<tr><td><b>${esc(item.sensorName)}</b><small>${esc(item.latestScenario || 'normal')}</small></td><td>${c(item.latestTemperatureC)}</td><td><span class="condition ${String(item.status).toLowerCase().replace('_', '-')}">${esc(item.status).replace('_', ' ')}</span></td><td>${item.readingCount}</td><td>${item.status === 'TOO_WARM' || item.status === 'TOO_COLD' ? 'Needs inspection' : 'Online'}</td></tr>`).join('');
    return `<div class="proto-header"><div><span class="proto-kicker">PROTOTYPE C · FLEET RELIABILITY</span><h2>Find repeat equipment risk before the next excursion.</h2><p>A supervisor view that combines temperature compliance with data quality and maintenance signals.</p></div><button type="button" data-action="review">Create maintenance review</button></div><div class="proto-fleet-kpis"><div><span>In range</span><b>${(statusCounts.STABLE || 0) + (statusCounts.ACCEPTABLE || 0)}/${m.latest.length || '—'}</b><small>latest sensor status</small></div><div><span>Excursions</span><b>${m.related.length}</b><small>in persisted sample</small></div><div><span>Data quality</span><b>94%</b><small>simulated confidence</small></div><div><span>Maintenance</span><b>${m.breaches.length}</b><small>units need inspection</small></div></div><div class="proto-fleet-grid"><section class="proto-panel"><h3>Units at risk</h3><table class="proto-table"><thead><tr><th>Storage unit</th><th>Latest</th><th>Condition</th><th>Readings</th><th>Health</th></tr></thead><tbody>${rows || '<tr><td colspan="5">Waiting for event data</td></tr>'}</tbody></table></section><section class="proto-panel"><h3>Maintenance signals</h3><div class="proto-signal"><b>Compressor duty cycle</b><span>Pod 03 · 91% for 42 min</span><i style="width:91%"></i></div><div class="proto-signal"><b>Door activity</b><span>Pod 12 · 7 openings in 1 hr</span><i style="width:68%"></i></div><div class="proto-signal"><b>Sensor freshness</b><span>All simulated sensors reporting</span><i style="width:22%"></i></div><p class="proto-safety">Equipment indicators are simulated prototype values; connect device telemetry before using operationally.</p></section></div>${workflowView()}`;
  }

  function workflowView() { return `<section class="proto-workflow"><span>In-memory prototype state</span><b>Acknowledgement: ${esc(workflow.acknowledgement)}</b><b>Review: ${esc(workflow.review)}</b><b>Note: ${esc(workflow.note)}</b><b>Disposition: ${esc(workflow.disposition)}</b></section>`; }
  function render() { const m = model(); target.innerHTML = variant === 'A' ? variantA(m) : variant === 'B' ? variantB(m) : variantC(m); target.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => { const action = button.dataset.action; if (action === 'ack') workflow.acknowledgement = 'Acknowledged by demo operator'; if (action === 'review') { workflow.review = 'Qualified review started'; workflow.disposition = 'Pending qualified review'; } if (action === 'note') workflow.note = 'Operator note added (simulated)'; if (action === 'resolve') workflow.note = 'Temperature recovered — stock review remains required'; render(); })); }
  function switchTo(next) { variant = next; query.set('variant', next); global.history.replaceState({}, '', global.location.pathname + '?' + query.toString()); render(); updateBar(); }
  function updateBar() { const label = document.getElementById('prototypeVariantLabel'); if (label) label.textContent = variant + ' — ' + names[variant]; }
  function addSwitcher() { const bar = document.createElement('nav'); bar.className = 'prototype-switcher'; bar.setAttribute('aria-label', 'Analytics prototype variations'); bar.innerHTML = '<button type="button" data-proto="previous" aria-label="Previous variant">←</button><strong id="prototypeVariantLabel"></strong><button type="button" data-proto="next" aria-label="Next variant">→</button>'; document.body.appendChild(bar); bar.addEventListener('click', (event) => { const direction = event.target.dataset.proto; if (!direction) return; const index = keys.indexOf(variant); switchTo(keys[(index + (direction === 'next' ? 1 : keys.length - 1)) % keys.length]); }); global.addEventListener('keydown', (event) => { if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return; const tag = document.activeElement?.tagName; if (tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement?.isContentEditable) return; const index = keys.indexOf(variant); switchTo(keys[(index + (event.key === 'ArrowRight' ? 1 : keys.length - 1)) % keys.length]); }); updateBar(); }
  document.body.classList.add('prototype-mode'); addSwitcher(); render();
  bridge.watchDatabase((raw) => { events = raw.map((event) => data.normalizeEvent(event)); render(); }, () => { events = []; render(); });
})(typeof globalThis === 'undefined' ? this : globalThis);
