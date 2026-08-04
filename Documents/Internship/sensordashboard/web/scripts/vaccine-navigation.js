(function exposeVaccineNavigation(root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else {
    root.VaccineNavigation = factory();
    if (root.document) root.VaccineNavigation.mountNavigation(root.document, root.document.body.dataset.vaccineView);
  }
})(typeof globalThis === 'undefined' ? this : globalThis, function vaccineNavigationFactory() {
  const VIEWS = Object.freeze([
    Object.freeze({ id: 'analytics', label: 'Analytics', href: 'domain-vaccine.html' }),
    Object.freeze({ id: 'raw-events', label: 'Raw Events', href: 'domain-vaccine-raw.html' }),
    Object.freeze({ id: 'inference', label: 'Inference', href: 'domain-vaccine-inference.html' }),
  ]);

  function renderNavigation(activeView) {
    return `<nav class="vaccine-tabs" aria-label="Vaccine dashboard views">${VIEWS.map((view) => {
      const active = view.id === activeView;
      return `<a href="${view.href}" class="vaccine-tab${active ? ' active' : ''}"${active ? ' aria-current="page"' : ''}>${view.label}</a>`;
    }).join('')}</nav>`;
  }

  function mountNavigation(documentRef, activeView) {
    const target = documentRef.querySelector('[data-vaccine-tabs]');
    if (target) target.innerHTML = renderNavigation(activeView);
  }

  return { VIEWS, renderNavigation, mountNavigation };
});
