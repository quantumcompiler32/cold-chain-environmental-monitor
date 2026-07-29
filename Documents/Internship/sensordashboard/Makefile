PYTHON ?= .venv/bin/python
APP_ENV ?= development
LISTENER_OUTPUT_MODE ?= verbose

.PHONY: test reset-demo verify start-infrastructure start-listener run-scenario start-dashboard stop-demo

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

reset-demo:
	@if [ "$(RESET_CONFIRM)" != "YES" ]; then echo "Refusing reset. Re-run with RESET_CONFIRM=YES and --confirm-reset is applied by this target."; exit 1; fi
	APP_ENV=$(APP_ENV) $(PYTHON) scripts/reset_demo.py --confirm-reset

verify:
	$(PYTHON) scripts/verify_persistence.py

start-infrastructure:
	brew services start postgresql@16
	brew services start mosquitto

start-listener:
	$(PYTHON) -m services.temperature_subscriber --write-db --output-mode $(LISTENER_OUTPUT_MODE)

run-scenario:
	$(PYTHON) -m services.temperature_event_generator --scenario $(SCENARIO) --count $(or $(COUNT),30) --interval-ms $(or $(INTERVAL_MS),100) --output-mode $(or $(OUTPUT_MODE),summary) --seed $(or $(SEED),42)

start-dashboard:
	$(PYTHON) -m services.dashboard_bridge

stop-demo:
	brew services stop mosquitto
	brew services stop postgresql@16
