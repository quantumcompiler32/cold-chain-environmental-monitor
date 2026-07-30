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

try:
    from services.event_contract import parse_timestamp
except ImportError:  # pragma: no cover
    from event_contract import parse_timestamp


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

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

    def fetch_latest_events(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        """Return the bounded newest-event verification view."""
        return self.fetch_events(filters, latest_first=True, limit=100)

    def export_csv(self, filters: dict[str, str] | None = None) -> str:
        """Export every stored event, not the browser's filtered view."""
        # Make a blank in-memory document, then write the header and rows into it.
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for event in self.fetch_events(filters):
            writer.writerow([event.get(column, "") for column in CSV_COLUMNS])
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


class DashboardHandler(BaseHTTPRequestHandler):
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

    def _csv(self, content: str) -> None:
        # Send CSV as a download rather than displaying it as a web page.
        body = content.encode("utf-8")
        self.send_response(200)
        self._headers("text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=temperature_events.csv")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
                status_counts: dict[str, int] = {}
                scenario_counts: dict[str, int] = {}
                severity_counts: dict[str, int] = {}
                for event in events:
                    status_counts[event["operational_status"]] = status_counts.get(event["operational_status"], 0) + 1
                    scenario_counts[event["scenario"]] = scenario_counts.get(event["scenario"], 0) + 1
                    severity_counts[event["severity"]] = severity_counts.get(event["severity"], 0) + 1
                self._json(200, {
                    "count": len(events),
                    "status_counts": status_counts,
                    "scenario_counts": scenario_counts,
                    "severity_counts": severity_counts,
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
