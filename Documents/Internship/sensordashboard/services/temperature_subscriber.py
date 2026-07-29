#!/usr/bin/env python3
"""Validate MQTT events and atomically persist generic and vaccine records."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

import paho.mqtt.client as mqtt
import psycopg

try:
    from services.event_contract import format_timestamp, now_utc, parse_timestamp
    from services.terminal_output import format_event_block, format_service_message
    from services.temperature_uncertainty import enrich_event
except ImportError:  # pragma: no cover
    from event_contract import format_timestamp, now_utc, parse_timestamp
    from terminal_output import format_event_block, format_service_message
    from temperature_uncertainty import enrich_event


MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "devices/temperature")


def postgres_settings() -> dict[str, Any]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres")),
        **({"password": os.environ["POSTGRES_PASSWORD"]} if os.environ.get("POSTGRES_PASSWORD") else {}),
    }


def connect_database():
    return psycopg.connect(**postgres_settings())


REQUIRED_FIELDS = {
    "event_id",
    "device_id",
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
}


@dataclass(frozen=True)
class PersistenceResult:
    event_id: str
    duplicate: bool
    received_at: datetime
    stored_at: datetime | None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Listen for vaccine temperature events from MQTT.")
    parser.add_argument("--write-db", action="store_true", help="Persist validated events to PostgreSQL.")
    parser.add_argument(
        "--output-mode",
        choices=("none", "verbose"),
        default="verbose",
        help="Live terminal output detail (default: verbose).",
    )
    return parser.parse_args()


def validate_event(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the shared event contract."""
    if not isinstance(data, dict):
        raise ValueError("The JSON payload must be an object.")

    normalized = dict(data)
    if "event_time" not in normalized and "timestamp" in normalized:
        normalized["event_time"] = normalized["timestamp"]
    if "source_time" not in normalized and "source_timestamp" in normalized:
        normalized["source_time"] = normalized["source_timestamp"]
    missing = sorted(REQUIRED_FIELDS - normalized.keys())
    if missing:
        raise ValueError("Missing required field(s): " + ", ".join(missing))

    try:
        normalized["event_time"] = parse_timestamp(normalized.get("event_time"), "event_time", assume_utc=False)
        normalized["source_time"] = (
            None if normalized.get("source_time") in (None, "")
            else parse_timestamp(normalized.get("source_time"), "source_time")
        )
        normalized["temperature_c"] = float(normalized["temperature_c"])
        normalized["sensor_tolerance_c"] = float(normalized["sensor_tolerance_c"])
        normalized["temperature_min_possible_c"] = float(normalized["temperature_min_possible_c"])
        normalized["temperature_max_possible_c"] = float(normalized["temperature_max_possible_c"])
        normalized["storage_min_c"] = float(normalized["storage_min_c"])
        normalized["storage_max_c"] = float(normalized["storage_max_c"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid event value: {exc}") from exc

    for field in ("event_id", "device_id", "sensor_name", "vaccine_type", "scenario", "status", "uncertainty_status", "measurement_confidence"):
        if not isinstance(normalized[field], str) or not normalized[field].strip():
            raise ValueError(f"{field} must be a non-empty string.")
    try:
        UUID(normalized["event_id"])
    except ValueError as exc:
        raise ValueError("event_id must be a UUID") from exc
    if not isinstance(normalized["boundary_crossing"], bool):
        raise ValueError("boundary_crossing must be boolean.")

    expected = enrich_event(normalized, normalized["storage_min_c"], normalized["storage_max_c"])
    for field in (
        "sensor_tolerance_c",
        "temperature_min_possible_c",
        "temperature_max_possible_c",
        "uncertainty_status",
        "boundary_crossing",
    ):
        if normalized[field] != expected[field]:
            raise ValueError(f"{field} does not match temperature_c and uncertainty.")

    normalized["timestamp"] = normalized["event_time"]
    normalized["source_timestamp"] = normalized["source_time"]
    return normalized


def _json_payload(event: dict[str, Any]) -> str:
    payload = dict(event)
    for key in ("event_time", "source_time", "timestamp", "source_timestamp"):
        if isinstance(payload.get(key), datetime):
            payload[key] = format_timestamp(payload[key])
    return json.dumps(payload, sort_keys=True)


def persist_event(
    event: dict[str, Any],
    *,
    connection_factory: Callable[[], Any] = connect_database,
    received_at: datetime | None = None,
    clock: Callable[[], datetime] | None = None,
    topic: str = MQTT_TOPIC,
) -> PersistenceResult:
    """Write both records in one transaction using the event's stable ID."""
    normalized = validate_event(event)
    received = received_at or now_utc(clock)
    stored = now_utc(clock)
    generic_sql = """
        INSERT INTO telemetry_logs
            (event_id, device_id, topic, event_time, payload, temperature, status, received_at, stored_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING event_id
    """
    vaccine_sql = """
        INSERT INTO vaccine_temperature_events
            (event_id, device_id, sensor_name, vaccine_type, scenario, scenario_phase,
             temperature_c, status, sensor_tolerance_c, temperature_min_possible_c,
             temperature_max_possible_c, storage_min_c, storage_max_c, uncertainty_status,
             boundary_crossing, measurement_confidence, source_time, event_time,
             received_at, stored_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING event_id
    """
    params_generic = (
        normalized["event_id"], normalized["device_id"], topic,
        normalized["event_time"], _json_payload(normalized), normalized["temperature_c"],
        normalized["status"], received, stored,
    )
    params_vaccine = (
        normalized["event_id"], normalized["device_id"], normalized["sensor_name"],
        normalized["vaccine_type"], normalized["scenario"], normalized.get("scenario_phase"),
        normalized["temperature_c"], normalized["status"], normalized["sensor_tolerance_c"],
        normalized["temperature_min_possible_c"], normalized["temperature_max_possible_c"],
        normalized["storage_min_c"], normalized["storage_max_c"], normalized["uncertainty_status"],
        normalized["boundary_crossing"], normalized["measurement_confidence"],
        normalized["source_time"], normalized["event_time"], received, stored,
    )

    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute(generic_sql, params_generic)
            generic_inserted = cursor.fetchone() is not None
            cursor.execute(vaccine_sql, params_vaccine)
            vaccine_inserted = cursor.fetchone() is not None

    duplicate = not generic_inserted or not vaccine_inserted
    logging.getLogger(__name__).info(
        json.dumps({
            "event": "event_persisted",
            "event_id": normalized["event_id"],
            "duplicate": duplicate,
            "generic_inserted": generic_inserted,
            "vaccine_inserted": vaccine_inserted,
        }, sort_keys=True)
    )
    return PersistenceResult(normalized["event_id"], duplicate, received, None if duplicate else stored)


def process_message(
    payload: bytes | str,
    *,
    connection_factory: Callable[[], Any] = connect_database,
    clock: Callable[[], datetime] | None = None,
    topic: str = MQTT_TOPIC,
) -> PersistenceResult:
    """Decode, validate, timestamp ingestion, and persist one MQTT message."""
    received_at = now_utc(clock)
    data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    return persist_event(
        data,
        connection_factory=connection_factory,
        received_at=received_at,
        clock=clock,
        topic=topic,
    )


def verify_database() -> int:
    with connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.telemetry_logs'), to_regclass('public.vaccine_temperature_events')")
            generic_table, vaccine_table = cursor.fetchone()
            if generic_table is None or vaccine_table is None:
                raise RuntimeError("Run database/bootstrap/001_core.sql before starting the listener.")
            cursor.execute("SELECT COUNT(*) FROM vaccine_temperature_events")
            return cursor.fetchone()[0]


def main() -> int:
    args = parse_arguments()
    message_count = 0
    if args.write_db:
        try:
            existing_rows = verify_database()
        except (psycopg.Error, RuntimeError) as exc:
            print(f"POSTGRESQL SETUP ERROR: {exc}", file=sys.stderr)
            return 1
        if args.output_mode == "verbose":
            print(format_service_message("LISTENER", f"PostgreSQL connected; existing vaccine rows: {existing_rows}"), flush=True)

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            if args.output_mode == "verbose":
                print(format_service_message("LISTENER", f"MQTT connection failed: {reason_code}"), flush=True)
            return
        client.subscribe(MQTT_TOPIC, qos=0)
        if args.output_mode == "verbose":
            print(format_service_message(
                "LISTENER",
                f"MQTT connected; topic={MQTT_TOPIC}; database_writing={'ENABLED' if args.write_db else 'DISABLED'}",
            ), flush=True)

    def on_message(client, userdata, message):
        nonlocal message_count
        message_count += 1
        try:
            # Capture listener receipt before validation or database work. The
            # value is passed through so it cannot be confused with stored_at.
            received_at = now_utc()
            event = validate_event(json.loads(message.payload.decode("utf-8")))
            if args.write_db:
                result = persist_event(event, received_at=received_at, topic=message.topic)
                if args.output_mode == "verbose":
                    print(format_event_block(
                        event,
                        component="LISTENER",
                        outcome="DUPLICATE" if result.duplicate else "PERSISTED",
                        sequence=message_count,
                        topic=message.topic,
                        received_at=result.received_at,
                        stored_at=result.stored_at,
                    ), flush=True)
            elif args.output_mode == "verbose":
                print(format_event_block(
                    event,
                    component="LISTENER",
                    outcome="VALIDATED (DATABASE WRITE DISABLED)",
                    sequence=message_count,
                    topic=message.topic,
                    received_at=received_at,
                ), flush=True)
        except (json.JSONDecodeError, ValueError) as exc:
            logging.getLogger(__name__).error(json.dumps({"event": "event_rejected", "error": str(exc)}))
            if args.output_mode == "verbose":
                print(format_service_message("LISTENER", f"REJECTED #{message_count:04d}: {exc}"), file=sys.stderr, flush=True)
        except psycopg.Error as exc:
            logging.getLogger(__name__).exception(json.dumps({"event": "database_write_failed", "error": str(exc)}))
            if args.output_mode == "verbose":
                print(format_service_message("LISTENER", f"DATABASE ERROR #{message_count:04d}: {exc}"), file=sys.stderr, flush=True)

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except (ConnectionRefusedError, OSError) as exc:
        print(format_service_message("LISTENER", f"MQTT CONNECTION ERROR: {exc}"), file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("\n" + format_service_message("LISTENER", "Stopping temperature subscriber."), flush=True)
    finally:
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
