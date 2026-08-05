# The Makefile is the command index for the local demo. Long-running services
# are deliberately separate targets so their ownership is unambiguous:
# PostgreSQL/Mosquitto are infrastructure, the subscriber writes PostgreSQL,
# the bridge reads PostgreSQL, and the generator publishes MQTT events.
PYTHON ?= .venv/bin/python
APP_ENV ?= development
LISTENER_OUTPUT_MODE ?= verbose
START_TIME ?=

.PHONY: test e2e reset-demo reset-dashboard verify verify-fast train-models start-infrastructure start-listener start-ml-service run-scenario demo-all start-dashboard stop-demo

test:
	$(PYTHON) -m unittest discover -s backend/tests -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s db/tests -p 'test_*.py' -v
	$(PYTHON) -m unittest discover -s ai_worker/tests -p 'test_*.py' -v
	node --test frontend/tests/*.test.js

e2e:
	APP_ENV=test $(PYTHON) backend/e2e_verify.py

reset-demo:
	@if [ "$(RESET_CONFIRM)" != "YES" ]; then echo "Refusing reset. Re-run with RESET_CONFIRM=YES."; exit 1; fi
	APP_ENV=$(APP_ENV) $(PYTHON) db/reset_demo.py --confirm-reset

reset-dashboard:
	APP_ENV=$(APP_ENV) $(PYTHON) db/reset_dashboard.py

verify:
	$(PYTHON) db/verify_persistence.py

verify-fast:
	$(PYTHON) db/verify_database.py

train-models:
	$(PYTHON) -m ai_worker.train_models --vaccine $(or $(VACCINE),pfizer_ultralow)

start-infrastructure:
	# Infrastructure must be healthy before the listener can consume events.
	brew services start postgresql@16
	brew services start mosquitto

start-listener:
	# The subscriber owns the normal MQTT-to-PostgreSQL write path.
	$(PYTHON) -m backend.temperature_subscriber --write-db --output-mode $(LISTENER_OUTPUT_MODE)

run-scenario:
	$(PYTHON) -m backend.temperature_event_generator --sensor $(or $(SENSORS),Pod1) --scenario $(SCENARIO) --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),100) --output-mode $(or $(OUTPUT_MODE),summary) --seed $(or $(SEED),42) $(if $(START_TIME),--start-time "$(START_TIME)",)

demo-all:
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod1 --scenario normal --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod2 --scenario warning --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod3 --scenario outlier --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary)
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod4 --scenario normal --occupancy-state offline --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod5 --scenario normal --occupancy-state empty --no-cooling-enabled --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod6 --scenario normal --occupancy-state empty --cooling-enabled --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m backend.temperature_event_generator --sensor Pod7 Pod8 Pod9 Pod10 Pod11 Pod12 Pod13 Pod14 Pod15 Pod16 Pod17 Pod18 Pod19 Pod20 --scenario normal --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42

start-dashboard:
	# The bridge is read-only; serve the frontend/ directory separately on port 8766.
	$(PYTHON) -m backend.dashboard_bridge

start-ml-service:
	$(PYTHON) -m ai_worker.ml_service

stop-demo:
	brew services stop mosquitto
	brew services stop postgresql@16
