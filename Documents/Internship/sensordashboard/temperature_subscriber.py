#!/usr/bin/env python3
"""Validate MQTT temperature events and optionally persist them in PostgreSQL.

Without ``--write-db`` this program is a console listener. With the flag it
also checks the table, inserts each event, and prints the generated row ID so
the full MQTT-to-database path can be demonstrated.
"""

import argparse
import json
import sys
from datetime import datetime

import paho.mqtt.client as mqtt
import psycopg

# MQTT settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "devices/temperature"

# PostgreSQL settings
# This Mac uses the local PostgreSQL role "mokshjoshi" with no password.
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "iotdb"
POSTGRES_USER = "mokshjoshi"

REQUIRED_FIELDS = {
    "device_id",
    "timestamp",
    "source_timestamp",
    "sensor_name",
    "vaccine_type",
    "scenario",
    "temperature_c",
    "status",
}


def parse_arguments():
    """Read whether this listener should write received events to PostgreSQL."""
    parser = argparse.ArgumentParser(
        description="Listen for temperature events from MQTT."
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Print each event and insert it into PostgreSQL.",
    )
    return parser.parse_args()


def connect_database():
    """Open a passwordless local PostgreSQL connection."""
    # Keep database settings in one small function so the validation and write
    # paths use the same local connection configuration.
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
    )


def verify_database():
    """Verify PostgreSQL, the table, provenance columns, and current row count."""
    # Check the schema before listening so a typo or older table fails with a
    # useful setup message instead of failing on the first MQTT event.
    with connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.temperature_events');")
            table_name = cursor.fetchone()[0]

            if table_name is None:
                raise RuntimeError(
                    "The table temperature_events does not exist. "
                    "Run: psql -d iotdb -f create_temperature_table.sql"
                )

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'temperature_events';
                """
            )
            columns = {row[0] for row in cursor.fetchall()}
            missing_columns = {"vaccine_type", "scenario"} - columns
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise RuntimeError(
                    f"The table is missing: {missing}. "
                    "Run: psql -U mokshjoshi -d iotdb -f create_temperature_table.sql"
                )

            cursor.execute("SELECT COUNT(*) FROM temperature_events;")
            existing_rows = cursor.fetchone()[0]

    return existing_rows


def validate_event(data):
    """Validate the required JSON shape and normalize temperature to a float."""
    # The subscriber accepts only the portable event contract shared with the
    # dashboard and the database table.
    if not isinstance(data, dict):
        raise ValueError("The JSON payload must be an object.")

    missing = sorted(REQUIRED_FIELDS - data.keys())
    if missing:
        raise ValueError(
            "Missing required field(s): " + ", ".join(missing)
        )

    try:
        data["temperature_c"] = float(data["temperature_c"])
    except (TypeError, ValueError) as exc:
        raise ValueError("temperature_c must be numeric.") from exc

    for field in REQUIRED_FIELDS - {"temperature_c"}:
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"{field} must be a non-empty string.")

    return data


def write_event_to_database(data):
    """Insert one validated event and return its generated database ID."""
    # Use parameters rather than string interpolation so event values cannot
    # change the SQL statement.
    insert_sql = """
        INSERT INTO temperature_events
        (
            device_id,
            event_timestamp,
            source_timestamp,
            sensor_name,
            vaccine_type,
            scenario,
            temperature_c,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """

    with connect_database() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                insert_sql,
                (
                    data["device_id"],
                    data["timestamp"],
                    data["source_timestamp"],
                    data["sensor_name"],
                    data["vaccine_type"],
                    data["scenario"],
                    data["temperature_c"],
                    data["status"],
                ),
            )
            inserted_id = cursor.fetchone()[0]

    return inserted_id


def print_event(data):
    # The terminal format mirrors the readable raw-event page for quick demos.
    print("\n" + "=" * 60)
    print("RECEIVED TEMPERATURE EVENT")
    print("=" * 60)
    print(f"Device:          {data['device_id']}")
    print(f"Sensor:          {data['sensor_name']}")
    print(f"Vaccine profile: {data['vaccine_type']}")
    print(f"Scenario:        {data['scenario']}")
    print(f"Temperature:     {data['temperature_c']:.2f}°C")
    print(f"Status:          {data['status']}")
    print(f"Source time:     {data['source_timestamp']}")
    print(f"Event time:      {data['timestamp']}")
    print(f"Received locally:{datetime.now().isoformat(timespec='seconds')}")


def main():
    """Connect to MQTT and process events until the user presses Ctrl+C."""
    args = parse_arguments()

    if args.write_db:
        try:
            existing_rows = verify_database()
            print("PostgreSQL connection: OK")
            print(f"Database: {POSTGRES_DB}")
            print("Table: temperature_events")
            print(f"Existing rows: {existing_rows}")
        except (psycopg.Error, RuntimeError) as exc:
            print(f"POSTGRESQL SETUP ERROR: {exc}", file=sys.stderr)
            return 1

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        # MQTT invokes this callback after the connection handshake; subscribe
        # only after success so reconnects restore the topic subscription.
        if reason_code != 0:
            print(f"MQTT connection failed: {reason_code}")
            return

        client.subscribe(MQTT_TOPIC, qos=0)

        print(f"MQTT connection: OK")
        print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Topic: {MQTT_TOPIC}")
        print(
            "Database writing: "
            + ("ENABLED" if args.write_db else "DISABLED")
        )
        print("Press Ctrl+C to stop.")

    def on_message(client, userdata, message):
        # Every MQTT payload follows the same path: decode JSON, validate the
        # required fields, print it, then optionally insert it in PostgreSQL.
        try:
            payload_text = message.payload.decode("utf-8")
            data = validate_event(json.loads(payload_text))
            print_event(data)

            if args.write_db:
                inserted_id = write_event_to_database(data)
                print("Database write: SUCCESS")
                print(f"Inserted row ID: {inserted_id}")
            else:
                print("Database write: SKIPPED (--write-db not supplied)")

        except json.JSONDecodeError as exc:
            print(f"Invalid JSON received: {exc}")
        except ValueError as exc:
            print(f"Event validation failed: {exc}")
        except psycopg.Error as exc:
            print(f"Database write: FAILED")
            print(f"PostgreSQL error: {exc}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        # loop_forever owns the network loop until Ctrl+C or a connection error.
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except (ConnectionRefusedError, OSError) as exc:
        print(f"MQTT CONNECTION ERROR: {exc}", file=sys.stderr)
        print(
            "Make sure Mosquitto is running on localhost:1883.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nStopping temperature subscriber.")
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
