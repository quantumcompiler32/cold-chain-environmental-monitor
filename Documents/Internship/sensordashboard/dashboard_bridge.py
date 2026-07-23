#!/usr/bin/env python3
"""Read-only HTTP adapter for the vaccine dashboard.

The event generator, Mosquitto broker, and PostgreSQL subscriber run as
independent terminal services. This process never starts a generator, listens
to MQTT, or writes to PostgreSQL. It only reads persisted events for the
browser and exports the same database rows as CSV.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from datetime import date, datetime, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

# These are the PostgreSQL column names selected by the adapter. Keep the
# order stable so the CSV export is deterministic and easy to load in Colab.
EVENT_COLUMNS = (
    "id",
    "device_id",
    "event_timestamp",
    "source_timestamp",
    "sensor_name",
    "vaccine_type",
    "scenario",
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
    "received_at",
)

CSV_COLUMNS = (
    "event_id",
    "device_id",
    "timestamp",
    "source_timestamp",
    "sensor_name",
    "vaccine_type",
    "scenario",
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
    "received_at",
)

EVENT_QUERY = """
SELECT id, device_id, event_timestamp, source_timestamp, sensor_name,
       vaccine_type, scenario, temperature_c, status, sensor_tolerance_c,
       temperature_min_possible_c, temperature_max_possible_c, storage_min_c,
       storage_max_c, uncertainty_status, boundary_crossing,
       measurement_confidence, received_at
FROM temperature_events
ORDER BY event_timestamp ASC, id ASC
"""


class DatabaseUnavailable(RuntimeError):
    """Raised when the dashboard cannot read PostgreSQL."""


def postgres_settings() -> dict[str, Any]:
    """Build connection settings without exposing credentials to the client."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", "mokshjoshi"),
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
    return value


class DatabaseReader:
    """Deep read-only module behind the dashboard's small HTTP interface."""

    def __init__(
        self,
        connect_factory: Callable[..., Any] = connect_postgres,
        settings: dict[str, Any] | None = None,
    ):
        self.connect_factory = connect_factory
        self.settings = settings if settings is not None else postgres_settings()

    def _connect(self):
        try:
            return self.connect_factory(**self.settings)
        except DatabaseUnavailable:
            raise
        except Exception as exc:
            raise DatabaseUnavailable(str(exc)) from exc

    def _rows(self, query: str) -> list[dict[str, Any]]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    # The adapter cannot mutate data even if a future query is
                    # accidentally changed from SELECT to a write statement.
                    cursor.execute("SET TRANSACTION READ ONLY")
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    columns = []
                    for column in cursor.description:
                        name = getattr(column, "name", None)
                        columns.append(name if name is not None else column[0])
        except DatabaseUnavailable:
            raise
        except Exception as exc:
            raise DatabaseUnavailable(str(exc)) from exc

        return [
            {column: serialize_value(value) for column, value in zip(columns, row)}
            for row in rows
        ]

    def check(self) -> None:
        """Verify that PostgreSQL is reachable without changing its state."""
        self._rows("SELECT 1")

    def fetch_events(self) -> list[dict[str, Any]]:
        """Return every stored event in dashboard vocabulary and DB order."""
        rows = self._rows(EVENT_QUERY)
        events = []
        for row in rows:
            event = {
                "event_id": str(row["id"]),
                "device_id": row["device_id"],
                "timestamp": row["event_timestamp"],
                "source_timestamp": row["source_timestamp"] or "",
                "sensor_name": row["sensor_name"],
                "vaccine_type": row["vaccine_type"],
                "scenario": row["scenario"],
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
                "received_at": row["received_at"],
            }
            events.append(event)
        return events

    def export_csv(self) -> str:
        """Export every stored event, not the browser's filtered view."""
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for event in self.fetch_events():
            writer.writerow([event.get(column, "") for column in CSV_COLUMNS])
        return output.getvalue()


class DashboardHandler(BaseHTTPRequestHandler):
    reader: DatabaseReader

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

    def _csv(self, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(200)
        self._headers("text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=temperature_events.csv")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            try:
                self.reader.check()
                self._json(200, {"ok": True, "database_connected": True, "read_only": True})
            except DatabaseUnavailable as exc:
                self._json(200, {"ok": True, "database_connected": False, "read_only": True, "error": str(exc)})
            return
        if path == "/api/events":
            try:
                events = self.reader.fetch_events()
                self._json(200, {"events": events, "count": len(events), "source": "postgresql"})
            except DatabaseUnavailable as exc:
                self._json(503, {"error": str(exc), "database_connected": False})
            return
        if path == "/api/events/export.csv":
            try:
                self._csv(self.reader.export_csv())
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
    parser = argparse.ArgumentParser(description="Run the read-only vaccine dashboard database adapter.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    DashboardHandler.reader = DatabaseReader()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Read-only dashboard adapter: http://{args.host}:{args.port}")
    print("Source: PostgreSQL temperature_events")
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
