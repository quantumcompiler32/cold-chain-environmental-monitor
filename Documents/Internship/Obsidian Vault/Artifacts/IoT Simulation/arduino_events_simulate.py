from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

BROKER_HOST = os.getenv("IOT_MQTT_HOST", "localhost")
BROKER_PORT = int(os.getenv("IOT_MQTT_PORT", "1883"))
INTERVAL_SECONDS = float(os.getenv("IOT_SIM_INTERVAL", "5"))

DEVICES = (
    {
        "device_id": "arduino-dht22",
        "topic": "devices/arduino-dht22/telemetry",
        "has_humidity": True,
        "has_pressure": False,
    },
    {
        "device_id": "esp32-bmp280",
        "topic": "devices/esp32-bmp280/telemetry",
        "has_humidity": False,
        "has_pressure": True,
    },
)


def build_payload(device: dict[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "device_id": device["device_id"],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "temperature": round(random.uniform(68.0, 82.0), 2),
        "status": "online",
    }

    if device["has_humidity"]:
        payload["humidity"] = round(random.uniform(35.0, 65.0), 2)

    if device["has_pressure"]:
        payload["pressure"] = round(random.uniform(995.0, 1025.0), 2)

    return payload


def connect_with_retry(client: mqtt.Client) -> None:
    while True:
        try:
            client.connect(BROKER_HOST, BROKER_PORT, 60)
            return
        except OSError as error:
            print(
                f"MQTT unavailable at {BROKER_HOST}:{BROKER_PORT}: {error}. "
                "Retrying in 3 seconds. Run 'iot on' in another terminal if needed."
            )
            time.sleep(3)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    connect_with_retry(client)
    client.loop_start()

    print(f"Publishing to MQTT at {BROKER_HOST}:{BROKER_PORT}")
    print(f"Interval: {INTERVAL_SECONDS} seconds")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            for device in DEVICES:
                payload = build_payload(device)
                message = json.dumps(payload)
                result = client.publish(str(device["topic"]), message, qos=0)
                result.wait_for_publish(timeout=10)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f"Publish failed with MQTT code {result.rc}: {message}")
                else:
                    print(f"Published {device['topic']}: {message}")

            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
