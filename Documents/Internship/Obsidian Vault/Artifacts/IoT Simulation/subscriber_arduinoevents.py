from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
import paho.mqtt.client as mqtt
import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MQTT_HOST = os.getenv("IOT_MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("IOT_MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("IOT_MQTT_TOPIC", "devices/+/telemetry")

DB_CONFIG = {
    "dbname": os.getenv("IOT_DB_NAME", "iot_platform"),
    "user": os.getenv("IOT_DB_USER", os.getenv("USER", "postgres")),
    "password": os.getenv("IOT_DB_PASSWORD") or None,
    "host": os.getenv("IOT_DB_HOST", "localhost"),
    "port": int(os.getenv("IOT_DB_PORT", "5432")),
    "connect_timeout": 5,
}


def insert_payload(payload: dict[str, Any]) -> None:
    device_id = payload.get("device_id")
    if not device_id:
        raise ValueError("Payload is missing device_id.")

    timestamp = payload.get("timestamp") or datetime.now().isoformat(timespec="seconds")

    query = """
        INSERT INTO telemetry_logs (
            device_id,
            timestamp,
            temperature,
            humidity,
            pressure,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s);
    """

    values = (
        device_id,
        timestamp,
        payload.get("temperature"),
        payload.get("humidity"),
        payload.get("pressure"),
        payload.get("status", "online"),
    )

    with psycopg2.connect(**DB_CONFIG) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)


def on_connect(
    client: mqtt.Client,
    userdata: Any,
    flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: Optional[mqtt.Properties],
) -> None:
    if reason_code != 0:
        print(f"MQTT connection failed: {reason_code}")
        return

    print(f"Connected to MQTT at {MQTT_HOST}:{MQTT_PORT}")
    print(f"Subscribed to {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC)


def on_disconnect(
    client: mqtt.Client,
    userdata: Any,
    disconnect_flags: mqtt.DisconnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: Optional[mqtt.Properties],
) -> None:
    if reason_code != 0:
        print(f"MQTT connection lost ({reason_code}); the client will retry.")


def on_message(
    client: mqtt.Client,
    userdata: Any,
    message: mqtt.MQTTMessage,
) -> None:
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object.")
        print(f"Received {message.topic}: {payload}")
        insert_payload(payload)
        print("Inserted into PostgreSQL.")
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}")
    except Exception as error:
        print(f"Processing failed: {error}")
        print("Run 'iot doctor' in another terminal for environment checks.")


def connect_with_retry(client: mqtt.Client) -> None:
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            return
        except OSError as error:
            print(
                f"MQTT unavailable at {MQTT_HOST}:{MQTT_PORT}: {error}. "
                "Retrying in 3 seconds. Run 'iot on' in another terminal if needed."
            )
            time.sleep(3)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=10)
    connect_with_retry(client)

    print("Subscriber starting. Press Ctrl+C to stop.")
    try:
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        print("\nSubscriber stopped.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
