# Learning record: generator event identity

- Date: 2026-08-05
- Lesson: [0001 — From a reading to a publishable event](../lessons/0001-from-reading-to-event.html)
- Status: understood with one clarification

## Demonstrated understanding

The learner correctly explained that the CSV timestamp belongs to historical source data, while `event_time` is created for the newly generated simulated event. They correctly distinguished `event_id` as the identity of one event from `run_id` as a shared identifier across events from one generator invocation.

## Clarification needed

The learner initially treated MQTT as the broker. Clarified that Mosquitto is the broker; the generator publishes and the subscriber consumes. Clarified that `run_id` supports grouping and diagnostics across a generator run.

## Next zone

Teach the subscriber trust boundary: decoding, JSON parsing, validation, normalization, and timestamp separation before persistence.
