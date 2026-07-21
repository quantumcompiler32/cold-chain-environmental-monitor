# Internship Context And Glossary

## Canonical terms

- **ByteSmart** — the project/work context for environmental and cold-chain monitoring, analysis, and related learning artifacts.
- **Bitwise** — Bitwise Academy, the internship context and reporting audience.
- **Reading** — one timestamped measurement from a dataset or sensor stream.
- **Event** — a JSON representation of a reading published through MQTT and persisted by the database listener.
- **Excursion** — a reading or period outside a configured temperature range; it is an investigation signal, not a product-release decision.
- **Relatively warm** — a project-defined analytical label, not a clinical or regulatory conclusion.
- **Stable** — a project-defined pattern of readings that remains within the selected analysis boundaries.
- **Needs investigation** — a project status indicating that the data deserves review by a qualified person.
- **K-Means** — an exploratory clustering method that groups patterns; it does not prove that a real failure occurred.
- **Model label** — a derived training target that must be created without leaking the answer into the features.

## Boundaries

- Hobby-grade sensors and a cooler experiment cannot replace certified vaccine-monitoring equipment.
- Air temperature is not automatically equivalent to product temperature.
- ML output supports exploration and explanation; it does not authorize medical, safety, potency, use, or discard decisions.

## Related notes

- [[ByteSmart Project]]
- [[Bitwise Internship Timeline]]

