# Vaccine-Temperature Pipeline Resources

## Knowledge

- [PostgreSQL Documentation](https://www.postgresql.org/docs/current/)
  Use for understanding databases, `psql`, tables, SQL queries, and `COPY` exports.
- [Eclipse Paho MQTT Python Documentation](https://eclipse.dev/paho/files/paho.mqtt.python/html/)
  Use for understanding MQTT clients, publishing, subscribing, and callbacks.
- [Python argparse Documentation](https://docs.python.org/3/library/argparse.html)
  Use for understanding command-line flags such as `--scenario` and `--max-events`.
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
  Use for understanding the automated tests in this project.
- [Python pickle Documentation](https://docs.python.org/3/library/pickle.html)
  Use for understanding how the saved model bundle is serialized and loaded.
- [Flask Quickstart](https://flask.palletsprojects.com/en/stable/quickstart/)
  Use for understanding how the standalone HTTP inference service exposes routes.

## Local project sources

- `/Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project/temperature_event_generator.py`
  The implementation of profiles, scenarios, status classification, JSON creation, and MQTT publishing.
- `/Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project/temperature_subscriber.py`
  The implementation of MQTT subscription, validation, and PostgreSQL writes.
- `/Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project/analyze_temperature_database.py`
  The implementation of the readable analysis report.
- `/Users/mokshjoshi/Projects/iot_workspace/projects/temperature_iot_project/create_temperature_table.sql`
  The PostgreSQL schema and indexes.

## ML inference lesson sources

- `/Users/mokshjoshi/Documents/Internship/sensordashboard/services/train_models.py`
  The command-line entry point that trains and saves the local model bundle.
- `/Users/mokshjoshi/Documents/Internship/sensordashboard/services/ml_inference.py`
  The feature extraction, three educational models, bundle loading, prediction contract, and Flask routes.
- `/Users/mokshjoshi/Documents/Internship/sensordashboard/services/ml_service.py`
  The standalone process that starts the read-only inference service on port 5000.
- `/Users/mokshjoshi/Documents/Internship/sensordashboard/web/scripts/vaccine-inference.js`
  The browser-to-service request contract.
- `/Users/mokshjoshi/Documents/Internship/sensordashboard/web/scripts/vaccine-inference-page.js`
  The Inference tab form, service status, submission, and result rendering.
