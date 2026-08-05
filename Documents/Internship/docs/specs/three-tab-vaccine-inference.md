# Three-tab vaccine dashboard and one-event inference integration

## Problem Statement

The real vaccine cold-chain dashboard already has the operational analytics
view, the PostgreSQL-backed raw event view, and a separately runnable Phase 1
inference page. They are not presented as one simple workflow, so an operator
has to know which page to open for each task.

The model workflow is also easy to misunderstand. The CSV is used for
exploratory data analysis and one-time training. The trained model bundle is
saved once. Runtime inference should load that saved bundle, accept one new
Temperature event with optional recent context, and return an advisory
prediction without retraining or changing stored data.

The current local serving layout can also make the inference page unreachable
when the dashboard website is served from a narrower directory. The new
navigation must use a stable, locally runnable route.

## Solution

Add three primary tabs to the top header of the real vaccine dashboard:

1. `Analytics` — the existing operational monitoring and trend view.
2. `Raw Events` — the existing read-only persisted event stream.
3. `Inference` — the existing one-event form connected to the read-only Flask
   inference service.

The three destinations should share the Phase 1 visual skin, display a clear
active-tab state, support direct links, and remain simple to use. The Inference
tab should reuse the current saved-model and Flask service boundary rather than
moving model code into the browser or adding training to the dashboard.

## User Stories

1. As a cold-chain operator, I want to see Analytics, Raw Events, and Inference
   in one header, so that I can move between the three workflows without
   returning to a separate prototype page.
2. As a cold-chain operator, I want the active tab to be visually obvious, so
   that I always know which dashboard surface I am using.
3. As a cold-chain operator, I want the Analytics tab to open the existing
   operational monitoring view, so that the new navigation does not remove
   current temperature, Pod, scenario, or trend behavior.
4. As a cold-chain operator, I want the Raw Events tab to open the persisted
   PostgreSQL event stream, so that I can inspect the evidence behind an
   Analytics status.
5. As a cold-chain operator, I want the Inference tab to open a small form, so
   that I can submit one Temperature event without preparing a CSV upload.
6. As a cold-chain operator, I want to enter a Pod, temperature, vaccine
   profile, and scenario, so that the service receives the minimum useful event
   data.
7. As a cold-chain operator, I want a Use latest event action when persisted
   data is available, so that I can test inference without retyping a recent
   event.
8. As a cold-chain operator, I want the dashboard to send one event and
   optional recent context over HTTP, so that inference remains focused and
   understandable.
9. As a cold-chain operator, I want the service to load the saved model bundle,
   so that prediction does not retrain on every request.
10. As a cold-chain operator, I want the Inference result to identify the
    algorithm, model version, sample basis, and validation measure, so that I
    can understand what the result means.
11. As a cold-chain operator, I want the primary out-of-range probability to
    be easy to find, so that I can use it as review context.
12. As a cold-chain operator, I want secondary temperature-trend and Pod-group
    results when available, so that the three trained model outputs are visible
    without overwhelming the form.
13. As a cold-chain operator, I want an explicit insufficient-data result, so
    that the dashboard does not present an unsupported prediction as fact.
14. As a cold-chain operator, I want an explicit service-unavailable result,
    so that I know to start the local inference service instead of assuming the
    event was processed.
15. As a cold-chain operator, I want a missing-model result to explain that the
    model bundle must be trained first, so that the local setup is recoverable.
16. As a cold-chain operator, I want inference submissions to remain read-only,
    so that testing a prediction cannot create or modify a Temperature event.
17. As a cold-chain operator, I want raw operational status to remain separate
    from ML-assisted analysis, so that a model result cannot automatically
    declare affected stock safe, unsafe, released, or quarantined.
18. As a data analyst, I want EDA to remain a standalone CSV/Colab workflow,
    so that exploratory charts and pattern discovery do not clutter the
    operational dashboard.
19. As a data analyst, I want training to remain an explicit one-time action,
    so that the saved model bundle is reproducible and easy to explain.
20. As a developer, I want the three tabs to use a stable local route, so that
    serving the dashboard from the documented local command does not produce a
    404 for Inference.
21. As a developer, I want the existing Flask HTTP contract to remain small,
    so that the dashboard integration does not require a second prediction
    implementation.
22. As a developer, I want the existing Analytics and Raw Events behavior to
    remain intact, so that navigation is an additive workflow improvement.
23. As a reviewer, I want direct links to each tab to work independently, so
    that a page can be opened from a runbook or browser bookmark.
24. As a reviewer, I want the three tabs to retain the same visual skin, so
    that the integrated dashboard feels like one product rather than a mix of
    prototypes.
25. As a reviewer, I want the local dashboard to remain usable when PostgreSQL
    or the ML service is offline, so that unavailable states are honest and the
    UI can still be visually reviewed.

## Implementation Decisions

- The highest integration seam is the vaccine dashboard header navigation. The
  three tabs link the existing Analytics, Raw Events, and Inference surfaces;
  model training, EDA, PostgreSQL persistence, and inference calculation stay
  behind their existing boundaries.
- The user-facing labels are `Analytics`, `Raw Events`, and `Inference`.
  Existing internal route names may remain compatible where that avoids
  unnecessary migration, but the visible workflow should use these three
  labels.
- The active tab is represented in the URL and in the visual state, allowing
  direct links and browser refresh without losing the selected destination.
- The three surfaces use the existing Phase 1 visual skin and a consistent
  header treatment. Navigation must remain keyboard accessible and must not
  depend on hover alone.
- Analytics remains the primary operational monitoring view for Pod events,
  excursions, borderline readings, scenarios, and temperature trends.
- Raw Events remains a read-only view of persisted PostgreSQL Temperature
  events. The tab does not become a data-upload workflow.
- Inference reuses the current one-event form. The minimum editable fields are
  Pod, temperature in °C, vaccine profile, and scenario. Recent persisted
  context may be included automatically when available.
- The dashboard sends one `Inference request` to the separately started local
  `Inference service` over HTTP. The service loads the saved model bundle and
  does not train, persist the submitted event, or change affected-stock
  disposition.
- The response presents logistic regression as the primary out-of-range
  probability and may present the existing linear-regression and k-means
  results as secondary advisory context. Each result identifies its algorithm,
  data basis, model version, sample count, and validation measure when those
  values exist.
- The UI distinguishes ready, unavailable, missing-model, invalid-request, and
  insufficient-data states. No fabricated prediction is shown when the
  service cannot provide a supported result.
- EDA remains outside the dashboard. The CSV/Colab workflow may create charts,
  detect patterns, and train models, but the dashboard only consumes saved
  artifacts at inference time.
- The documented local serving arrangement must expose the dashboard and
  Inference destination through one stable route. The implementation must not
  rely on a sibling directory that is invisible when the website is served
  from a narrower directory.
- The existing read-only ML boundary in ADR-0008 remains in force.
- This intentionally makes the Phase 1 experience reachable from the real
  dashboard, so ADR-0007 should be revisited: the visual/navigation update is
  no longer only a separately reachable prototype, even though existing
  operational behavior remains preserved.

## Testing Decisions

- Tests should verify observable behavior at the highest available seam:
  selecting a tab changes the destination, the active state follows the URL,
  and each destination loads from the documented local server root.
- Add a browser or static navigation smoke test covering all three tabs and
  direct-link refreshes. A successful test must verify that the Inference link
  does not return 404.
- Extend the existing Phase 1 inference tests to verify that the form builds
  one event, includes optional context, calls the read-only HTTP endpoint, and
  renders the returned advisory result.
- Test the ML service contract for healthy readiness, missing model artifacts,
  malformed requests, valid one-event requests, and read-only behavior.
- Test the saved-model workflow separately: training reads the CSV and writes
  the bundle; inference loads the bundle without retraining.
- Test that an inference request does not create a PostgreSQL event or alter
  operational status and disposition data.
- Manually inspect the real dashboard at desktop and narrow widths. Confirm
  the three tabs remain readable, the active state is clear, the form is short,
  and offline states are honest.
- Reuse existing prior art in the Phase 1 route, adapter, inference, service,
  dashboard bridge, and JavaScript test suites. Prefer contract-level tests
  over tests that assert private helper structure or CSS implementation.

## Out of Scope

- Training a model on every inference request.
- Uploading a CSV or batch of 100+ events through the Inference tab.
- Moving EDA charts or exploratory analysis into the operational dashboard.
- Replacing the saved-model workflow with browser-side training.
- Automatic quarantine, release, safe/unsafe declaration, or clinical
  disposition based on an ML result.
- Production deployment, authentication, cloud hosting, or external API
  access.
- Adding a fourth dashboard tab for Summary/Impact.
- Rebuilding the existing Analytics or Raw Events behavior.
- Making ML a hidden dependency for the dashboard's operational monitoring.

## Further Notes

- The current local workflow is intentionally educational and local-first:
  inspect or analyze the CSV, train once, save the model bundle, start the
  inference service, then submit one event from the dashboard.
- The initial implementation should optimize for a short form and clear
  mechanics rather than prediction sophistication. A future enhancement may
  evaluate a short event window instead of one event, but that is not needed
  for this integration.
- The Inference tab should explain that ML-assisted analysis is review context
  and that raw Temperature event status remains authoritative for operations.
