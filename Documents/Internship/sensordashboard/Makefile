# The Makefile is the command index for the local demo. Long-running services
# are deliberately separate targets so their ownership is unambiguous:
# PostgreSQL/Mosquitto are infrastructure, the subscriber writes PostgreSQL,
# the bridge reads PostgreSQL, and the generator publishes MQTT events.
PYTHON ?= .venv/bin/python
APP_ENV ?= development
LISTENER_OUTPUT_MODE ?= verbose

.PHONY: test e2e reset-demo reset-dashboard verify verify-fast train-models start-infrastructure start-listener start-ml-service run-scenario demo-all start-dashboard stop-demo

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

e2e:
	APP_ENV=test $(PYTHON) scripts/e2e_verify.py

reset-demo:
	@if [ "$(RESET_CONFIRM)" != "YES" ]; then echo "Refusing reset. Re-run with RESET_CONFIRM=YES and --confirm-reset is applied by this target."; exit 1; fi
	APP_ENV=$(APP_ENV) $(PYTHON) scripts/reset_demo.py --confirm-reset

reset-dashboard:
	APP_ENV=$(APP_ENV) $(PYTHON) scripts/reset_dashboard.py

verify:
	$(PYTHON) scripts/verify_persistence.py

verify-fast:
	$(PYTHON) scripts/verify_database.py

train-models:
	$(PYTHON) -m services.train_models --vaccine $(or $(VACCINE),pfizer_ultralow)

start-infrastructure:
	# Infrastructure must be healthy before the listener can consume events.
	brew services start postgresql@16
	brew services start mosquitto

start-listener:
	# The subscriber owns the normal MQTT-to-PostgreSQL write path.
	$(PYTHON) -m services.temperature_subscriber --write-db --output-mode $(LISTENER_OUTPUT_MODE)

run-scenario:
	$(PYTHON) -m services.temperature_event_generator --sensor $(or $(SENSORS),Pod1) --scenario $(SCENARIO) --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),100) --output-mode $(or $(OUTPUT_MODE),summary) --seed $(or $(SEED),42)

demo-all:
	$(PYTHON) -m services.temperature_event_generator --sensor Pod1 --scenario normal --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m services.temperature_event_generator --sensor Pod2 --scenario warning --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m services.temperature_event_generator --sensor Pod3 --scenario outlier --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary)
	$(PYTHON) -m services.temperature_event_generator --sensor Pod4 --scenario normal --occupancy-state offline --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m services.temperature_event_generator --sensor Pod5 --scenario normal --occupancy-state empty --no-cooling-enabled --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m services.temperature_event_generator --sensor Pod6 --scenario normal --occupancy-state empty --cooling-enabled --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42
	$(PYTHON) -m services.temperature_event_generator --sensor Pod7 Pod8 Pod9 Pod10 Pod11 Pod12 Pod13 Pod14 Pod15 Pod16 Pod17 Pod18 Pod19 Pod20 --scenario normal --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),200) --output-mode $(or $(OUTPUT_MODE),summary) --seed 42

start-dashboard:
	# The bridge is read-only; serve the web/ directory separately on port 8766.
	$(PYTHON) -m services.dashboard_bridge

start-ml-service:
	$(PYTHON) -m services.ml_service

stop-demo:
	brew services stop mosquitto
	brew services stop postgresql@16
