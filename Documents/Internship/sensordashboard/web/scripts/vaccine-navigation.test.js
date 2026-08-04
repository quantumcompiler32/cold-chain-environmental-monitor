const assert = require('node:assert/strict');
const test = require('node:test');

const { VIEWS, renderNavigation } = require('./vaccine-navigation.js');

test('defines the three vaccine dashboard destinations in workflow order', () => {
  assert.deepEqual(VIEWS, [
    { id: 'analytics', label: 'Analytics', href: 'domain-vaccine.html' },
    { id: 'raw-events', label: 'Raw Events', href: 'domain-vaccine-raw.html' },
    { id: 'inference', label: 'Inference', href: 'domain-vaccine-inference.html' },
  ]);
});

test('renders one active accessible tab and two inactive tabs', () => {
  const markup = renderNavigation('inference');

  assert.match(markup, /aria-label="Vaccine dashboard views"/);
  assert.match(markup, /href="domain-vaccine.html"[^>]*>Analytics<\/a>/);
  assert.match(markup, /href="domain-vaccine-raw.html"[^>]*>Raw Events<\/a>/);
  assert.match(markup, /href="domain-vaccine-inference.html"[^>]*class="vaccine-tab active"[^>]*>Inference<\/a>/);
  assert.equal((markup.match(/class="vaccine-tab active"/g) || []).length, 1);
});
