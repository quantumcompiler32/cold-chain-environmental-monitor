#!/usr/bin/env python3
"""Read-only HTTP adapter for the vaccine dashboard.

High-school version: the browser is a customer, PostgreSQL is a filing
cabinet, and this program is the receptionist. The browser asks the
receptionist for records; the receptionist reads the cabinet and returns
JSON or CSV. The receptionist is deliberately not allowed to change it.

The event generator, Mosquitto broker, and PostgreSQL subscriber run as
independent terminal services. This process never starts a generator, listens
to MQTT, or writes to PostgreSQL. It only reads persisted events for the
browser and exports the same database rows as CSV.
"""

from __future__ import annotations

import argparse
# csv creates a spreadsheet-like download for the Export button.
import csv
# io.StringIO lets us build that CSV in memory instead of making a temporary file.
import io
# json turns Python dictionaries into data the browser understands.
import json
# os lets the user override database settings with environment variables.
import os
from datetime import date, datetime, time
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.parse import parse_qs
from uuid import UUID
from zoneinfo import ZoneInfo

try:
    from services.event_contract import parse_timestamp
except ImportError:  # pragma: no cover
    from event_contract import parse_timestamp


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
EVENT_NOTIFY_CHANNEL = "cold_chain_events"
RESET_NOTIFY_CHANNEL = "cold_chain_reset"
LIVE_SNAPSHOT_LIMIT = 2000

# These are the PostgreSQL column names selected by the adapter. Keep the
# order stable so the CSV export is deterministic and easy to load in Colab.
EVENT_COLUMNS = (
    "event_id",
    "device_id",
    "sensor_name",
    "vaccine_type",
    "scenario",
    "scenario_phase",
    "occupancy_state",
    "batch_id",
    "cooling_enabled",
    "operational_status",
    "severity",
    "rule_alert",
    "temperature_c",
    "status",
    "sensor_tolerance_c",
    "temperature_min_possible_c",
    "temperature_max_possible_c",
    "storage_min_c",
    "storage_max_c",
    "uncertainty_status",
    "boundary_crossing",
    "measurement_confidence",
    "event_time",
    "received_at",
    "stored_at",
    "ingestion_latency_ms",
    "event_age_seconds",
)

CSV_COLUMNS = (
    "event_id",
    "device_id",
    "sensor_name",
    "vaccine_type",
    "scenario",
    "scenario_phase",
    "occupancy_state",
    "batch_id",
    "cooling_enabled",
    "operational_status",
    "severity",
    "rule_alert",
    "temperature_c",
    "status",
    "sensor_tolerance_c",
    "temperature_min_possible_c",
    "temperature_max_possible_c",
    "storage_min_c",
    "storage_max_c",
    "uncertainty_status",
    "boundary_crossing",
    "measurement_confidence",
    "event_time",
    "received_at",
    "stored_at",
)

# The existing Colab notebook reads this research-file contract: a 65-column
# header followed by a sensor-ID row and a units row.  The live dashboard only
# produces Pod1–Pod20, so the other source channels remain empty rather than
# being fabricated.
COLAB_SOURCE_COLUMNS = (
    "date", "time", "Time Elapsed", "Pod20", "Pod19", "Pod18", "Pod17", "Pod16",
    "Pod15", "Pod14", "Pod13", "Pod12", "Pod11", "Pod10", "Pod9", "Pod7", "Pod5",
    "Pod8", "Pod6", "Pod4", "Pod3", "Pod1", "Pod2", "Ambient", "TC43", "TC44",
    "TC45", "TC46", "TC47", "TC48", "TC49", "TC50", "TC1", "TC2", "TC3",
    "TC4", "TC5", "TC6", "TC7", "TempT2", "TempT4", "TempT6", "TC12", "TC13",
    "TC14", "TempT7", "TC16", "TC17", "TC18", "TempT8", "TempT5", "TC21", "TC22",
    "TempT3", "TC24", "TC25", "TC26", "TempT1", "TC28", "TC29", "TC30", "O2",
    "CO2", "", "",
)
COLAB_SOURCE_METADATA = (
    "", "", "", "b20", "b19", "b18", "b17", "b16", "b15", "b14", "b13",
    "b12", "b11", "b10", "b9", "b7", "b5", "b8", "b6", "b4", "b3", "b1",
    "b2", "Toutside", "Te6", "Te5", "Te4", "Td6", "Td5", "Td4", "Tc5", "Tc4",
    "Tc6", "Tb4", "Tb5", "Tb6", "Ta4", "Ta5", "Ta6", "Ti9", "Th9", "Tg9",
    "Ta3", "Ta2", "Ta1", "Tf8", "Tb3", "Tb2", "Tb1", "Tf9", "Tg8", "Tc3",
    "Tc2", "Th8", "Td3", "Td2", "Td1", "Ti8", "Te3", "Te2", "Te1", "O2", "CO2",
    "", "",
)
COLAB_SOURCE_UNITS = (
    "", "", "", *(["F"] * 58), "%", "%", "", "",
)
COLAB_PODS = tuple(f"Pod{index}" for index in range(1, 21))
CALIFORNIA_TIMEZONE = ZoneInfo("America/Los_Angeles")

EVENT_SELECT = """
SELECT event_id, device_id, sensor_name, vaccine_type, scenario, scenario_phase,
       occupancy_state, batch_id, cooling_enabled, operational_status, severity, rule_alert,
       temperature_c, status, sensor_tolerance_c, temperature_min_possible_c,
       temperature_max_possible_c, storage_min_c, storage_max_c,
       uncertainty_status, boundary_crossing, measurement_confidence,
       event_time, received_at, stored_at,
       EXTRACT(EPOCH FROM (received_at - event_time)) * 1000 AS ingestion_latency_ms,
       EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - event_time)) AS event_age_seconds
FROM vaccine_temperature_events
"""

EVENT_QUERY = EVENT_SELECT + """
ORDER BY event_time ASC, event_id ASC
"""

LATEST_EVENT_QUERY = EVENT_SELECT + """
ORDER BY event_time DESC, event_id DESC
LIMIT 100
"""


class DatabaseUnavailable(RuntimeError):
    """Raised when the dashboard cannot read PostgreSQL."""


class InvalidFilter(ValueError):
    """Raised when a dashboard filter is malformed."""


def postgres_settings() -> dict[str, Any]:
    """Build connection settings without exposing credentials to the client."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres")),
        **({"password": os.environ["POSTGRES_PASSWORD"]} if os.environ.get("POSTGRES_PASSWORD") else {}),
    }


def connect_postgres(**settings):
    # Import lazily so the bridge can still be unit-tested without a local
    # driver or running PostgreSQL.
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on local setup
        raise DatabaseUnavailable("psycopg is not installed") from exc
    return psycopg.connect(**settings)


def serialize_value(value: Any) -> Any:
    """Convert PostgreSQL date/time values to JSON/CSV-safe values."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


class DatabaseReader:
    """Deep read-only module behind the dashboard's small HTTP interface."""

    def __init__(
        self,
        connect_factory: Callable[..., Any] = connect_postgres,
        settings: dict[str, Any] | None = None,
    ):
        # A "factory" is simply a function that knows how to open a database.
        # Keeping it injectable makes this class easy to test with a fake DB.
        self.connect_factory = connect_factory
        # Use supplied settings in tests; otherwise use the normal local DB.
        self.settings = settings if settings is not None else postgres_settings()

    def _connect(self):
        try:
            return self.connect_factory(**self.settings)
        except DatabaseUnavailable:
            raise
        except Exception as exc:
            raise DatabaseUnavailable(str(exc)) from exc

    def _rows(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        # Use a fresh connection for each request, then close it automatically.
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    # The adapter cannot mutate data even if a future query is
                    # accidentally changed from SELECT to a write statement.
                    # Make PostgreSQL enforce that this request cannot write.
                    cursor.execute("SET TRANSACTION READ ONLY")
                    cursor.execute("SET TIME ZONE 'UTC'")
                    cursor.execute(query, params) if params else cursor.execute(query)
                    rows = cursor.fetchall()
                    columns = []
                    for column in cursor.description:
                        name = getattr(column, "name", None)
                        columns.append(name if name is not None else column[0])
        except DatabaseUnavailable:
            raise
        except Exception as exc:
            raise DatabaseUnavailable(str(exc)) from exc

        # Pair each column name with the value in the same position in a row.
        # The result is easier for the rest of the program to use than tuples.
        return [
            {column: serialize_value(value) for column, value in zip(columns, row)}
            for row in rows
        ]

    def check(self) -> None:
        """Verify that PostgreSQL is reachable without changing its state."""
        self._rows("SELECT 1")

    def _map_events(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events = []
        for row in rows:
            event = {
                "event_id": str(row["event_id"]),
                "device_id": row["device_id"],
                "sensor_name": row["sensor_name"],
                "vaccine_type": row["vaccine_type"],
                "scenario": row["scenario"],
                "scenario_phase": row["scenario_phase"] or "",
                "occupancy_state": row["occupancy_state"] or "loaded",
                "batch_id": row["batch_id"] or "",
                "cooling_enabled": row["cooling_enabled"],
                "operational_status": row["operational_status"] or "NORMAL",
                "severity": row["severity"] or "info",
                "rule_alert": row["rule_alert"] or "",
                "temperature_c": row["temperature_c"],
                "status": row["status"],
                "sensor_tolerance_c": row["sensor_tolerance_c"],
                "temperature_min_possible_c": row["temperature_min_possible_c"],
                "temperature_max_possible_c": row["temperature_max_possible_c"],
                "storage_min_c": row["storage_min_c"],
                "storage_max_c": row["storage_max_c"],
                "uncertainty_status": row["uncertainty_status"],
                "boundary_crossing": row["boundary_crossing"],
                "measurement_confidence": row["measurement_confidence"],
                "event_time": row["event_time"],
                "received_at": row["received_at"],
                "stored_at": row["stored_at"],
                "ingestion_latency_ms": row["ingestion_latency_ms"],
                "event_age_seconds": row["event_age_seconds"],
            }
            # Keep the current frontend contract stable while it migrates to
            # the explicit timestamp names.
            event["timestamp"] = event["event_time"]
            events.append(event)
        return events

    def fetch_events(
        self,
        filters: dict[str, str] | None = None,
        *,
        latest_first: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return filtered events in a deterministic order."""
        where_sql, params = build_filter_sql(filters or {})
        order_sql = "ORDER BY event_time DESC, event_id DESC" if latest_first else "ORDER BY event_time ASC, event_id ASC"
        limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""
        query = EVENT_SELECT + where_sql + "\n" + order_sql + "\n" + limit_sql
        return self._map_events(self._rows(query, params))

    def fetch_latest_events(
        self,
        filters: dict[str, str] | None = None,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return the bounded newest-event verification view."""
        return self.fetch_events(filters, latest_first=True, limit=limit)

    def fetch_event(self, event_id: str) -> dict[str, Any] | None:
        """Read one committed event identified by the stable event ID."""
        query = EVENT_SELECT + "\nWHERE event_id = %s\nLIMIT 1"
        events = self._map_events(self._rows(query, (event_id,)))
        return events[0] if events else None

    def export_csv(self, filters: dict[str, str] | None = None) -> str:
        """Export every stored event, not the browser's filtered view."""
        # Make a blank in-memory document, then write the header and rows into it.
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for event in self.fetch_events(filters):
            writer.writerow([event.get(column, "") for column in CSV_COLUMNS])
        return output.getvalue()

    def export_colab_training_csv(self, filters: dict[str, str] | None = None) -> str:
        """Pivot live Pod events into the existing Test1 CSV contract for Colab."""
        events_by_pod = {pod: [] for pod in COLAB_PODS}
        for event in self.fetch_events(filters):
            pod = event.get("sensor_name")
            if pod in events_by_pod:
                events_by_pod[pod].append(event)

        row_count = max((len(events) for events in events_by_pod.values()), default=0)
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(COLAB_SOURCE_COLUMNS)
        writer.writerow(COLAB_SOURCE_METADATA)
        writer.writerow(COLAB_SOURCE_UNITS)

        first_time: datetime | None = None
        for row_index in range(row_count):
            round_events = [
                events[row_index]
                for events in events_by_pod.values()
                if row_index < len(events)
            ]
            event_times = [
                parse_timestamp(event["event_time"], "event_time", assume_utc=False)
                for event in round_events
            ]
            snapshot_time = min(event_times)
            first_time = first_time or snapshot_time
            local_time = snapshot_time.astimezone(CALIFORNIA_TIMEZONE)
            elapsed_seconds = int((snapshot_time - first_time).total_seconds())
            elapsed_hours, remainder = divmod(max(elapsed_seconds, 0), 3600)
            elapsed_minutes, elapsed_seconds = divmod(remainder, 60)
            row = ["" for _ in COLAB_SOURCE_COLUMNS]
            row[0] = local_time.strftime("%d-%b-%y")
            row[1] = local_time.strftime("%H:%M:%S")
            row[2] = f"{elapsed_hours}:{elapsed_minutes:02d}:{elapsed_seconds:02d}"
            for event in round_events:
                pod = event["sensor_name"]
                column = COLAB_SOURCE_COLUMNS.index(pod)
                fahrenheit = float(event["temperature_c"]) * 9.0 / 5.0 + 32.0
                row[column] = f"{fahrenheit:.4f}".rstrip("0").rstrip(".")
            writer.writerow(row)
        return output.getvalue()


FILTER_COLUMNS = {
    "pod": "sensor_name",
    "vaccine": "vaccine_type",
    "batch": "batch_id",
    "scenario": "scenario",
    "severity": "severity",
    "occupancy": "occupancy_state",
}


def build_filter_sql(filters: dict[str, str]) -> tuple[str, tuple[Any, ...]]:
    """Turn validated HTTP filters into SQL predicates and parameters."""
    clauses: list[str] = []
    params: list[Any] = []
    for query_name, column in FILTER_COLUMNS.items():
        value = filters.get(query_name)
        if value:
            clauses.append(f"{column} = %s")
            params.append(value)
    for query_name, operator in (("start", ">="), ("end", "<=")):
        value = filters.get(query_name)
        if value:
            try:
                params.append(parse_timestamp(value, query_name, assume_utc=False))
            except ValueError as exc:
                raise InvalidFilter(str(exc)) from exc
            clauses.append(f"event_time {operator} %s")
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", tuple(params)


def request_filters(path: str) -> dict[str, str]:
    """Extract the supported filters from a request URL."""
    query = parse_qs(urlparse(path).query)
    supported = set(FILTER_COLUMNS) | {"start", "end"}
    return {key: values[0] for key, values in query.items() if key in supported and values and values[0]}


def response_scope(filters: dict[str, str], events: list[dict[str, Any]]) -> dict[str, Any]:
    times = [event["event_time"] for event in events if event.get("event_time")]
    return {
        "filters": filters,
        "effective_start": filters.get("start") or (min(times) if times else None),
        "effective_end": filters.get("end") or (max(times) if times else None),
    }


def aggregate_analytics(events: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Count observed pod states, top-level scenarios, phases, and severity."""
    status_counts: dict[str, int] = {}
    scenario_counts: dict[str, int] = {}
    phase_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for event in events:
        status = event.get("operational_status", "UNKNOWN")
        scenario = event.get("scenario", "unknown")
        phase = event.get("scenario_phase") or scenario
        severity = event.get("severity", "info")
        status_counts[status] = status_counts.get(status, 0) + 1
        scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "status_counts": status_counts,
        "scenario_counts": scenario_counts,
        "phase_counts": phase_counts,
        "severity_counts": severity_counts,
    }


class DashboardHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    reader: DatabaseReader

    def _headers(self, content_type: str = "application/json") -> None:
        # These headers tell the browser what it received and prevent stale data.
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")

    def _json(self, status: int, payload: Any) -> None:
        # HTTP sends bytes, so first convert the Python object to JSON bytes.
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _csv(self, content: str, filename: str = "temperature_events.csv") -> None:
        # Send CSV as a download rather than displaying it as a web page.
        body = content.encode("utf-8")
        self.send_response(200)
        self._headers("text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename={filename}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse_headers(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _sse(self, event_name: str, payload: Any) -> None:
        body = f"event: {event_name}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")
        self.wfile.write(body)
        self.wfile.flush()

    def _event_stream(self) -> None:
        """Push committed event and demo-reset notifications to the browser."""
        # An SSE request owns its HTTP connection until the client closes it.
        # Prevent BaseHTTPRequestHandler from trying to parse a second request
        # after a browser tab or curl disconnects.
        self.close_connection = True
        self._sse_headers()
        try:
            with self.reader._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET TIME ZONE 'UTC'")
                    cursor.execute(f"LISTEN {EVENT_NOTIFY_CHANNEL}")
                    cursor.execute(f"LISTEN {RESET_NOTIFY_CHANNEL}")
                connection.commit()

                # LISTEN is active before the snapshot is read. Any event
                # committed during the snapshot is therefore queued and is
                # delivered after the browser receives its initial state.
                snapshot = self.reader.fetch_latest_events(limit=LIVE_SNAPSHOT_LIMIT)
                self._sse("snapshot", {
                    "events": list(reversed(snapshot)),
                    "count": len(snapshot),
                    "source": "postgresql",
                    "live_monitoring": True,
                    "scope": response_scope({}, snapshot),
                })

                while True:
                    notifications = connection.notifies(timeout=15)
                    delivered = False
                    for notification in notifications:
                        delivered = True
                        if notification.channel == RESET_NOTIFY_CHANNEL:
                            self._sse("reset", {
                                "events": [],
                                "count": 0,
                                "source": "postgresql",
                                "live_monitoring": True,
                                "reset": True,
                                "scope": response_scope({}, []),
                            })
                            continue
                        event = self.reader.fetch_event(notification.payload)
                        if event is not None:
                            self._sse("event", {
                                "event": event,
                                "source": "postgresql",
                                "live_monitoring": True,
                            })
                    if not delivered:
                        # Keep proxies and browser connections alive while no
                        # event is being generated. This is not a data poll.
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, DatabaseUnavailable):
            return

    def do_OPTIONS(self):
        # Browsers may ask permission before a cross-origin GET request.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        # GET means the browser is asking to read something.
        path = urlparse(self.path).path
        try:
            filters = request_filters(self.path)
        except InvalidFilter as exc:
            self._json(400, {"error": str(exc), "database_connected": True})
            return
        if path == "/health":
            try:
                self.reader.check()
                self._json(200, {"ok": True, "database_connected": True, "read_only": True})
            except DatabaseUnavailable as exc:
                self._json(200, {"ok": True, "database_connected": False, "read_only": True, "error": str(exc)})
            return
        if path == "/api/live/stream":
            self._event_stream()
            return
        if path in {"/api/events", "/api/live", "/api/verification/latest-events"}:
            try:
                latest = path == "/api/verification/latest-events"
                live = path == "/api/live"
                events = self.reader.fetch_latest_events(filters) if latest else self.reader.fetch_events(filters, latest_first=live, limit=200 if live else None)
                self._json(200, {
                    "events": events,
                    "count": len(events),
                    "source": "postgresql",
                    "latest_first": latest or live,
                    "live_monitoring": live,
                    "scope": response_scope(filters, events),
                })
            except DatabaseUnavailable as exc:
                self._json(503, {"error": str(exc), "database_connected": False})
            return
        if path == "/api/analytics":
            try:
                events = self.reader.fetch_events(filters)
                analytics = aggregate_analytics(events)
                self._json(200, {
                    "count": len(events),
                    **analytics,
                    "source": "postgresql",
                    "live_monitoring": False,
                    "scope": response_scope(filters, events),
                })
            except DatabaseUnavailable as exc:
                self._json(503, {"error": str(exc), "database_connected": False})
            return
        if path == "/api/events/export.csv":
            try:
                self._csv(self.reader.export_csv(filters))
            except DatabaseUnavailable as exc:
                self._json(503, {"error": str(exc), "database_connected": False})
            return
        if path == "/api/events/export-colab.csv":
            try:
                self._csv(
                    self.reader.export_colab_training_csv(filters),
                    "Test1_TempCO2O2.csv",
                )
            except DatabaseUnavailable as exc:
                self._json(503, {"error": str(exc), "database_connected": False})
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self):
        # Explicitly reject all mutation verbs; this adapter is read-only.
        self._json(405, {"error": "The dashboard bridge is read-only."})

    def log_message(self, format, *args):
        print(f"[dashboard-read-only] {self.address_string()} - {format % args}")


def main() -> int:
    # Command-line options allow a different host or port during development.
    parser = argparse.ArgumentParser(description="Run the read-only vaccine dashboard database adapter.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    # All incoming browser requests share this read-only database reader.
    DashboardHandler.reader = DatabaseReader()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Read-only dashboard adapter: http://{args.host}:{args.port}")
    print("Source: PostgreSQL vaccine_temperature_events")
    print("The event generator and MQTT subscriber must be run separately in the terminal.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
