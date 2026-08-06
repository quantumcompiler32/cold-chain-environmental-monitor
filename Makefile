# The Makefile is the command index for the local demo. Long-running services
# are deliberately separate targets so their ownership is unambiguous:
# PostgreSQL/Mosquitto are infrastructure, the subscriber writes PostgreSQL,
# the bridge reads PostgreSQL, and the generator publishes MQTT events.
PYTHON ?= .venv/bin/python
APP_ENV ?= development
LISTENER_OUTPUT_MODE ?= verbose
START_TIME ?=
DASHBOARD_RUNTIME_DIR ?= .runtime
DASHBOARD_PID_FILE ?= $(DASHBOARD_RUNTIME_DIR)/dashboard_bridge.pid
DASHBOARD_LOG_FILE ?= $(DASHBOARD_RUNTIME_DIR)/dashboard_bridge.log
DASHBOARD_URL ?= http://127.0.0.1:8787

.PHONY: e2e reset-demo reset-dashboard train-models start-infrastructure start-listener start-ml-service run-scenario demo-all start-dashboard watch-dashboard stop-dashboard stop-demo

e2e:
	APP_ENV=test $(PYTHON) backend/e2e_verify.py

reset-demo:
	@if [ "$(RESET_CONFIRM)" != "YES" ]; then echo "Refusing reset. Re-run with RESET_CONFIRM=YES."; exit 1; fi
	APP_ENV=$(APP_ENV) $(PYTHON) db/reset_demo.py --confirm-reset

reset-dashboard:
	APP_ENV=$(APP_ENV) $(PYTHON) db/reset_dashboard.py

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

# Start the read-only API/SSE server in the background. The static frontend is
# separate on port 8766; this bridge owns port 8787 and its PID is recorded in
# the project-local runtime directory for safe stop/watch operations.
start-dashboard:
	@mkdir -p "$(DASHBOARD_RUNTIME_DIR)"; \
	pid_file="$(DASHBOARD_PID_FILE)"; \
	if [ -f "$$pid_file" ]; then \
		pid=$$(tr -d '[:space:]' < "$$pid_file"); \
		case "$$pid" in \
			''|*[!0-9]*) echo "Removing invalid dashboard PID file: $$pid_file"; rm -f "$$pid_file"; pid="";; \
		esac; \
		if [ -n "$$pid" ] && kill -0 "$$pid" 2>/dev/null; then \
			cmd=$$(ps -p "$$pid" -o command= 2>/dev/null || true); \
			case "$$cmd" in \
				*backend.dashboard_bridge*) echo "Dashboard bridge already running (PID $$pid)."; exit 0;; \
				*) echo "Refusing to use $$pid_file: PID $$pid is not backend.dashboard_bridge."; exit 1;; \
			esac; \
		fi; \
		rm -f "$$pid_file"; \
	fi; \
	echo "Starting read-only dashboard bridge on port 8787..."; \
	nohup $(PYTHON) -m backend.dashboard_bridge >"$(DASHBOARD_LOG_FILE)" 2>&1 < /dev/null & \
	new_pid=$$!; \
	echo "$$new_pid" > "$$pid_file"; \
	sleep 0.25; \
	cmd=$$(ps -p "$$new_pid" -o command= 2>/dev/null || true); \
	case "$$cmd" in \
		*backend.dashboard_bridge*) echo "Dashboard bridge started (PID $$new_pid). Logs: $(DASHBOARD_LOG_FILE)";; \
		*) echo "Dashboard bridge failed to start. See $(DASHBOARD_LOG_FILE)."; rm -f "$$pid_file"; exit 1;; \
	esac

# Watch the live SSE stream and bridge HTTP log from a separate terminal while
# the bridge remains available for the frontend and other API clients. This
# target never starts or stops the bridge and never kills a process by port.
watch-dashboard:
	@pid_file="$(DASHBOARD_PID_FILE)"; \
	if [ ! -f "$$pid_file" ]; then echo "Dashboard bridge is not running (no PID file). Run make start-dashboard first."; exit 1; fi; \
	pid=$$(tr -d '[:space:]' < "$$pid_file"); \
	case "$$pid" in ''|*[!0-9]*) echo "Invalid dashboard PID file: $$pid_file"; exit 1;; esac; \
	if ! kill -0 "$$pid" 2>/dev/null; then echo "Dashboard bridge is already stopped (PID $$pid is not running)."; exit 1; fi; \
	cmd=$$(ps -p "$$pid" -o command= 2>/dev/null || true); \
	case "$$cmd" in *backend.dashboard_bridge*) ;; *) echo "Refusing to watch PID $$pid: it is not backend.dashboard_bridge."; exit 1;; esac; \
	if ! curl -fsS --max-time 2 "$(DASHBOARD_URL)/ready" >/dev/null; then echo "Dashboard bridge PID $$pid exists but $(DASHBOARD_URL)/ready is unavailable."; exit 1; fi; \
	log_file="$(DASHBOARD_LOG_FILE)"; \
	tail_pid=""; \
	cleanup() { if [ -n "$$tail_pid" ]; then kill "$$tail_pid" 2>/dev/null || true; wait "$$tail_pid" 2>/dev/null || true; fi; }; \
	trap cleanup EXIT; \
	if [ -f "$$log_file" ]; then tail -n 0 -f "$$log_file" & tail_pid=$$!; echo "Bridge log: $$log_file"; else echo "Bridge log unavailable: $$log_file"; fi; \
	echo "HTTP: GET $(DASHBOARD_URL)/ready"; \
	echo "SSE: GET $(DASHBOARD_URL)/api/live/stream (Ctrl-C stops the watcher only)."; \
	echo "Verbose curl output shows HTTP headers; bridge log lines show API calls and PostgreSQL reads."; \
	curl -v -N "$(DASHBOARD_URL)/api/live/stream"

# Stop only the bridge PID previously recorded by make start-dashboard. A live
# PID is checked with ps before SIGTERM so an unrelated process is never killed.
stop-dashboard:
	@pid_file="$(DASHBOARD_PID_FILE)"; \
	if [ ! -f "$$pid_file" ]; then echo "Dashboard bridge is already stopped (no PID file)."; exit 0; fi; \
	pid=$$(tr -d '[:space:]' < "$$pid_file"); \
	case "$$pid" in \
		''|*[!0-9]*) echo "Removing invalid dashboard PID file: $$pid_file"; rm -f "$$pid_file"; exit 1;; \
	esac; \
	if ! kill -0 "$$pid" 2>/dev/null; then echo "Dashboard bridge is already stopped (PID $$pid is not running)."; rm -f "$$pid_file"; exit 0; fi; \
	cmd=$$(ps -p "$$pid" -o command= 2>/dev/null || true); \
	case "$$cmd" in *backend.dashboard_bridge*) ;; *) echo "Refusing to stop PID $$pid: it is not backend.dashboard_bridge."; exit 1;; esac; \
	echo "Stopping dashboard bridge (PID $$pid)..."; \
	kill -TERM "$$pid"; \
	for attempt in $$(seq 1 50); do \
		if ! kill -0 "$$pid" 2>/dev/null; then rm -f "$$pid_file"; echo "Dashboard bridge stopped."; exit 0; fi; \
		sleep 0.1; \
	done; \
	echo "Dashboard bridge did not exit after SIGTERM; leaving $$pid_file in place."; exit 1

start-ml-service:
	$(PYTHON) -m ai_worker.ml_service

stop-demo:
	brew services stop mosquitto
	brew services stop postgresql@16
