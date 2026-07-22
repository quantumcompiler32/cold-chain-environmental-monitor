#!/usr/bin/env python3
"""Local HTTP/MQTT bridge for the vaccine dashboard live runner."""

from __future__ import annotations

import argparse
import json
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "devices/temperature"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
SCENARIOS = {"normal", "outlier", "failure", "recovery"}
SENSOR_PATTERN = re.compile(r"^Pod(?:[1-9]|1[0-9]|20)$", re.IGNORECASE)

PROFILES = {
    "pfizer_ultralow": {"id": "pfizer_ultralow", "label": "Pfizer ultralow", "target_c": -78.5, "min_c": -80.0, "max_c": -60.0},
    "moderna": {
        "id": "moderna",
        "label": "Moderna / Spikevax",
        "target_c": -32.5,
        "min_c": None,
        "max_c": None,
        "suggested_min_c": -50.0,
        "suggested_max_c": -15.0,
        "source_url": "https://products.modernatx.com/spikevaxpro/dosing-and-administration",
    },
}


def resolve_profile(profile_id: str, min_temp: Any = None, max_temp: Any = None) -> dict[str, Any]:
    """Return a validated profile payload suitable for the generator."""
    if profile_id not in PROFILES:
        raise ValueError(f"Unknown vaccine profile: {profile_id}")
    if (min_temp is None) != (max_temp is None):
        raise ValueError("Provide both min_temp and max_temp together.")
    profile = dict(PROFILES[profile_id])
    if profile["min_c"] is None and (min_temp is None or max_temp is None):
        raise ValueError("The Moderna profile requires custom min_temp and max_temp bounds.")
    if min_temp is not None:
        try:
            profile["min_c"] = float(min_temp)
            profile["max_c"] = float(max_temp)
        except (TypeError, ValueError) as exc:
            raise ValueError("Temperature bounds must be numeric.") from exc
    if profile["min_c"] >= profile["max_c"]:
        raise ValueError("min_temp must be less than max_temp.")
    return profile


def validate_start_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a browser start request at the public HTTP seam."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    profile_id = str(payload.get("profile", "pfizer_ultralow"))
    profile = resolve_profile(profile_id, payload.get("min_temp"), payload.get("max_temp"))
    scenario = str(payload.get("scenario", "outlier"))
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    sensors = payload.get("sensors")
    if not isinstance(sensors, list) or not sensors:
        raise ValueError("Select at least one Pod.")
    normalized_sensors = []
    for sensor in sensors:
        name = str(sensor)
        if not SENSOR_PATTERN.fullmatch(name):
            raise ValueError(f"Invalid Pod: {name}")
        if name not in normalized_sensors:
            normalized_sensors.append(name)
    try:
        interval_ms = int(payload.get("interval_ms", 500))
        max_events = int(payload.get("max_events", 20))
    except (TypeError, ValueError) as exc:
        raise ValueError("interval_ms and max_events must be integers.") from exc
    if interval_ms < 50:
        raise ValueError("interval_ms must be at least 50.")
    if max_events < 1 or max_events > 5000:
        raise ValueError("max_events must be between 1 and 5000.")
    return {
        "profile": profile,
        "scenario": scenario,
        "sensors": normalized_sensors,
        "interval_ms": interval_ms,
        "max_events": max_events,
        "save_to_database": bool(payload.get("save_to_database", False)),
    }


def build_generator_command(request: dict[str, Any], sensor: str, generator_path: Path) -> list[str]:
    """Build one deterministic child-process command for a selected Pod."""
    profile = request["profile"]
    command = [
        sys.executable,
        str(generator_path),
        "--sensor", sensor,
        "--vaccine-type", profile["id"],
        "--scenario", request["scenario"],
        "--interval-ms", str(request["interval_ms"]),
        "--max-events", str(request["max_events"]),
    ]
    if profile["id"] == "moderna":
        command.extend(["--min-temp", str(profile["min_c"]), "--max-temp", str(profile["max_c"])])
    return command


class DashboardState:
    """Own MQTT events, SSE subscribers, database writes, and run lifecycle."""

    def __init__(self, project_dir: Path, generator_path: Path):
        self.project_dir = project_dir
        self.generator_path = generator_path
        self.lock = threading.RLock()
        self.events: deque[dict[str, Any]] = deque(maxlen=12000)
        self.subscribers: set[queue.Queue[dict[str, Any]]] = set()
        self.event_sequence = 0
        self.run: dict[str, Any] = {"running": False, "state": "idle", "message": "Ready to run."}
        self.processes: dict[str, subprocess.Popen[str]] = {}
        self.mqtt_connected = False
        self.db_connection = None
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message

    def connect_mqtt(self) -> None:
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except OSError:
            self.mqtt_connected = False

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        self.mqtt_connected = reason_code == 0
        if self.mqtt_connected:
            client.subscribe(MQTT_TOPIC, qos=0)
        self.broadcast({"type": "bridge_status", "mqtt_connected": self.mqtt_connected})

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.mqtt_connected = False
        self.broadcast({"type": "bridge_status", "mqtt_connected": False})

    def _on_message(self, client, userdata, message):
        try:
            event = json.loads(message.payload.decode("utf-8"))
            if not isinstance(event, dict):
                return
            self.publish_event(event)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.broadcast({"type": "error", "message": "The bridge received invalid JSON from MQTT."})

    def publish_event(self, event: dict[str, Any]) -> None:
        with self.lock:
            self.event_sequence += 1
            enriched = dict(event)
            enriched["event_id"] = str(self.event_sequence)
            enriched["event_sequence"] = self.event_sequence
            enriched["received_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            if self.run["running"]:
                enriched["run_id"] = self.run["run_id"]
            self.events.append(enriched)
            if self.run["running"]:
                self.run["events_received"] = len(self.events)
            if self.db_connection is not None:
                self._write_database(enriched)
            payload = {"type": "event", "event": enriched}
        self.broadcast(payload)

    def _write_database(self, event: dict[str, Any]) -> None:
        with self.db_connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO temperature_events
                (device_id, event_timestamp, source_timestamp, sensor_name, vaccine_type, scenario, temperature_c, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (event.get("device_id"), event.get("timestamp"), event.get("source_timestamp") or None,
                 event.get("sensor_name"), event.get("vaccine_type"), event.get("scenario"),
                 float(event.get("temperature_c")), event.get("status")),
            )
        self.db_connection.commit()

    def add_subscriber(self) -> queue.Queue[dict[str, Any]]:
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=200)
        with self.lock:
            self.subscribers.add(subscriber)
            subscriber.put_nowait({"type": "run_status", **self.run})
        return subscriber

    def remove_subscriber(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        with self.lock:
            self.subscribers.discard(subscriber)

    def broadcast(self, payload: dict[str, Any]) -> None:
        with self.lock:
            for subscriber in list(self.subscribers):
                try:
                    subscriber.put_nowait(payload)
                except queue.Full:
                    try:
                        subscriber.get_nowait()
                        subscriber.put_nowait(payload)
                    except queue.Empty:
                        pass

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {**self.run, "events_received": len(self.events), "mqtt_connected": self.mqtt_connected}

    def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = validate_start_request(payload)
        with self.lock:
            if self.run["running"]:
                raise ValueError("A live run is already running.")
            if request["save_to_database"]:
                self._open_database()
            self.events.clear()
            run_id = uuid.uuid4().hex[:12]
            self.run = {"running": True, "state": "running", "run_id": run_id, "message": f"Starting {len(request['sensors'])} Pods…", "sensors": request["sensors"], "requested_events": len(request["sensors"]) * request["max_events"], "events_received": 0, "profile_id": request["profile"]["id"], "min_temp": request["profile"]["min_c"], "max_temp": request["profile"]["max_c"]}
            self.broadcast({"type": "run_status", **self.run})
            try:
                for sensor in request["sensors"]:
                    process = subprocess.Popen(
                        build_generator_command(request, sensor, self.generator_path),
                        cwd=self.project_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    self.processes[sensor] = process
                    threading.Thread(target=self._watch_process, args=(sensor, process, run_id), daemon=True).start()
            except OSError as exc:
                self._stop_processes_locked()
                self._finish_locked("failed", f"Could not start generator: {exc}")
                raise ValueError(str(exc)) from exc
        return self.status()

    def _watch_process(self, sensor: str, process: subprocess.Popen[str], run_id: str) -> None:
        stdout, stderr = process.communicate()
        with self.lock:
            self.processes.pop(sensor, None)
            if self.run.get("run_id") != run_id:
                return
            if process.returncode != 0 and self.run["state"] == "running":
                message = stderr.strip().splitlines()[-1] if stderr.strip() else f"{sensor} stopped with code {process.returncode}."
                self._stop_processes_locked()
                self._finish_locked("failed", message)
            elif not self.processes and self.run["state"] == "running":
                self._finish_locked("completed", "All selected Pods finished generating events.")

    def stop_run(self) -> dict[str, Any]:
        with self.lock:
            if not self.run["running"]:
                return self.status()
            self._stop_processes_locked()
            self._finish_locked("stopped", "Live run stopped.")
            return self.status()

    def _stop_processes_locked(self) -> None:
        processes = list(self.processes.values())
        self.processes.clear()
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    def _finish_locked(self, state: str, message: str) -> None:
        self.run.update({"running": False, "state": state, "message": message, "events_received": len(self.events)})
        if self.db_connection is not None:
            self.db_connection.close()
            self.db_connection = None
        self.broadcast({"type": "run_status", **self.run})

    def _open_database(self) -> None:
        try:
            import psycopg
            self.db_connection = psycopg.connect(host="localhost", port=5432, dbname="iotdb", user="mokshjoshi")
        except Exception as exc:
            raise ValueError(f"PostgreSQL is unavailable: {exc}") from exc


class DashboardHandler(BaseHTTPRequestHandler):
    state: DashboardState

    def _headers(self, content_type: str = "application/json") -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"ok": True, "mqtt_connected": self.state.mqtt_connected})
        elif path == "/api/profiles":
            self._json(200, list(PROFILES.values()))
        elif path == "/api/run/status":
            self._json(200, self.state.status())
        elif path == "/api/events":
            self._json(200, list(self.state.events))
        elif path == "/api/events/stream":
            self._stream()
        else:
            self._json(404, {"error": "Not found"})

    def _stream(self):
        subscriber = self.state.add_subscriber()
        self.send_response(200)
        self._headers("text/event-stream")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                try:
                    payload = subscriber.get(timeout=15)
                    self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.state.remove_subscriber(subscriber)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "Request body must be valid JSON."})
            return
        try:
            if path == "/api/run/start":
                result = self.state.start_run(payload)
                self._json(202, result)
            elif path == "/api/run/stop":
                self._json(200, self.state.stop_run())
            else:
                self._json(404, {"error": "Not found"})
        except ValueError as exc:
            self._json(400, {"error": str(exc)})

    def log_message(self, format, *args):
        print(f"[bridge] {self.address_string()} - {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local vaccine dashboard MQTT bridge.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    project_dir = Path(__file__).resolve().parent
    generator_path = project_dir / "temperature_event_generator.py"
    if not generator_path.exists():
        print(f"ERROR: generator not found at {generator_path}", file=sys.stderr)
        return 1
    state = DashboardState(project_dir, generator_path)
    DashboardHandler.state = state
    state.connect_mqtt()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard bridge: http://{args.host}:{args.port}")
    print(f"MQTT: {MQTT_BROKER}:{MQTT_PORT} ({'connected' if state.mqtt_connected else 'offline'})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop_run()
        state.mqtt_client.loop_stop()
        state.mqtt_client.disconnect()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
