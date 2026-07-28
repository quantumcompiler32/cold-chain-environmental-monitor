#!/usr/bin/env python3
"""Replay CSV temperature readings as scenario-labeled MQTT events.

The generator is the simulation side of the pipeline. It reads one sensor
column from the source CSV, converts Fahrenheit to Celsius, applies the
requested scenario, classifies the resulting temperature, and publishes a
JSON event to the shared MQTT topic.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import paho.mqtt.client as mqtt

from temperature_uncertainty import SENSOR_TOLERANCE_C, classify_uncertainty


# The local Mosquitto broker and topic shared with temperature_subscriber.py.
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "devices/temperature"

# The dataset is expected beside this script. Its thermocouple values are F.
CSV_FILE = "Test1_TempCO2O2.csv"
DEFAULT_SENSOR = "Pod1"
DEFAULT_INTERVAL_MS = 2000
# The source file is a Pfizer ultralow experiment. Keep its small variations
# while translating the baseline around the selected profile's target.
SOURCE_PROFILE_TARGET_C = -78.5
STABLE_TOLERANCE_C = 1.0
OUTLIER_OFFSET_C = 1.0
FAILURE_OFFSET_C = 5.0
SCENARIOS = ("normal", "outlier", "failure", "recovery")


@dataclass(frozen=True)
class VaccineProfile:
    """Temperature rules used to interpret one vaccine's readings.

    ``target_c`` is the preferred storage target. ``min_c`` and ``max_c``
    define the documented screening range used by classify_temperature().
    """

    name: str
    target_c: float
    min_c: float | None
    max_c: float | None


VACCINE_PROFILES = {
    "pfizer_ultralow": VaccineProfile(
        name="pfizer_ultralow",
        target_c=-78.5,
        min_c=-80.0,
        max_c=-60.0,
    ),
    "moderna": VaccineProfile(
        name="moderna",
        # The midpoint of the documented frozen-storage suggestion (-50 to
        # -15°C) is used as a neutral simulation target; the bounds are still
        # supplied explicitly by the dashboard so they remain editable.
        target_c=-32.5,
        min_c=None,
        max_c=None,
    ),
}


def resolve_profile(
    vaccine_type: str,
    *,
    min_temp: float | None = None,
    max_temp: float | None = None,
) -> VaccineProfile:
    """Resolve a built-in profile and validate any custom temperature bounds.

    Pfizer has fixed simulation bounds. Moderna requires both custom bounds
    so the operator can choose the frozen-storage range used by the run.
    """
    if (min_temp is None) != (max_temp is None):
        raise ValueError("Provide both --min-temp and --max-temp together.")

    try:
        profile = VACCINE_PROFILES[vaccine_type]
    except KeyError as exc:
        raise ValueError(f"Unknown vaccine profile: {vaccine_type}") from exc

    if profile.min_c is None and (min_temp is None or max_temp is None):
        raise ValueError(
            "The Moderna profile needs both --min-temp and --max-temp "
            "because the paper documents only its -30°C target."
        )

    resolved_min = profile.min_c if min_temp is None else min_temp
    resolved_max = profile.max_c if max_temp is None else max_temp
    assert resolved_min is not None and resolved_max is not None
    if resolved_min >= resolved_max:
        raise ValueError("--min-temp must be less than --max-temp.")

    return VaccineProfile(
        name=profile.name,
        target_c=profile.target_c,
        min_c=resolved_min,
        max_c=resolved_max,
    )


def parse_arguments() -> argparse.Namespace:
    """Read the command-line controls used to build the simulation."""
    parser = argparse.ArgumentParser(
        description="Replay CSV temperature readings to MQTT."
    )
    parser.add_argument(
        "--sensor",
        default=DEFAULT_SENSOR,
        help=f"Temperature column, for example Pod1 or Ambient (default: {DEFAULT_SENSOR}).",
    )
    parser.add_argument(
        "--csv-file",
        default=CSV_FILE,
        help="CSV file to replay; defaults to the bundled experiment file.",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=DEFAULT_INTERVAL_MS,
        help=f"Milliseconds between events (default: {DEFAULT_INTERVAL_MS}).",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="Maximum events to publish; 0 means unlimited.",
    )
    parser.add_argument(
        "--vaccine-type",
        choices=tuple(VACCINE_PROFILES),
        default="pfizer_ultralow",
        help="Vaccine profile used for classification.",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="normal",
        help="Controlled operating condition used for event generation.",
    )
    parser.add_argument(
        "--min-temp",
        type=float,
        help="Custom minimum temperature in °C; required with --max-temp for Moderna.",
    )
    parser.add_argument(
        "--max-temp",
        type=float,
        help="Custom maximum temperature in °C; required with --min-temp for Moderna.",
    )
    args = parser.parse_args()

    if args.interval_ms <= 0:
        parser.error("--interval-ms must be greater than zero.")
    if args.max_events < 0:
        parser.error("--max-events cannot be negative.")
    if args.scenario == "recovery" and args.max_events == 0:
        parser.error("--scenario recovery requires --max-events.")
    try:
        resolve_profile(
            args.vaccine_type,
            min_temp=args.min_temp,
            max_temp=args.max_temp,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return args


def classify_temperature(temperature_c: float, profile: VaccineProfile) -> str:
    """Classify one generated temperature using the profile's rules.

    Range checks happen before the stable-band check so a reading outside the
    documented range is always reported as too cold or too warm.
    """
    if profile.min_c is None or profile.max_c is None:
        raise ValueError("Temperature bounds are required for classification.")
    if temperature_c < profile.min_c:
        return "TOO_COLD"
    if temperature_c > profile.max_c:
        return "TOO_WARM"
    if abs(temperature_c - profile.target_c) <= STABLE_TOLERANCE_C:
        return "STABLE"
    return "ACCEPTABLE"


def adapt_source_temperature(source_temperature_c: float, profile: VaccineProfile) -> float:
    """Move a source variation around the selected profile's target.

    The bundled experiment was recorded for Pfizer ultralow storage. Reusing
    its raw Celsius value for Moderna would make every normal event look
    artificially too cold, so this keeps the measured variation but shifts
    its baseline to the selected profile target.
    """
    source_delta = source_temperature_c - SOURCE_PROFILE_TARGET_C
    return profile.target_c + source_delta


def transform_temperature(
    source_temperature_c: float,
    profile: VaccineProfile,
    scenario: str,
    event_number: int,
    total_events: int,
) -> float:
    """Apply deterministic scenario behavior to one source reading.

    Normal preserves the source value. Outlier injects occasional exceptions,
    failure holds a sustained warm excursion, and recovery interpolates from
    failure back to the profile target across the requested event count.
    """
    if profile.min_c is None or profile.max_c is None:
        raise ValueError("Temperature bounds are required for scenarios.")
    if event_number <= 0:
        raise ValueError("event_number must be positive.")

    if scenario == "normal":
        # Baseline simulation: preserve the source variation around the
        # selected vaccine profile rather than mixing Pfizer and Moderna
        # absolute baselines.
        return adapt_source_temperature(source_temperature_c, profile)
    if scenario == "outlier":
        # Every twentieth event is an intentional exception. Alternating the
        # direction gives the analysis report both cold and warm examples.
        if event_number % 20 != 0:
            return adapt_source_temperature(source_temperature_c, profile)
        outlier_number = event_number // 20
        if outlier_number % 2 == 1:
            return profile.min_c - OUTLIER_OFFSET_C
        return profile.max_c + OUTLIER_OFFSET_C
    if scenario == "failure":
        # A sustained warm excursion represents loss of cold-chain protection.
        return profile.max_c + FAILURE_OFFSET_C
    if scenario == "recovery":
        # Linear interpolation makes each event show progress back to target.
        if total_events <= 0:
            raise ValueError("Recovery requires a positive total event count.")
        failure_temperature = profile.max_c + FAILURE_OFFSET_C
        progress = (event_number - 1) / max(total_events - 1, 1)
        return failure_temperature + (
            profile.target_c - failure_temperature
        ) * progress
    raise ValueError(f"Unknown scenario: {scenario}")


def load_temperature_data(csv_path: Path, requested_sensor: str):
    """Load one sensor column and return usable timestamps and Celsius values."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path.resolve()}\n"
            "Place Test1_TempCO2O2.csv in the same folder as this program."
        )

    frame = pd.read_csv(csv_path, low_memory=False)
    if not {"date", "time"}.issubset(frame.columns):
        raise ValueError("The CSV must contain date and time columns.")

    excluded = {"date", "time", "Time Elapsed", "O2", "CO2"}
    columns = [
        c for c in frame.columns
        if c not in excluded and not str(c).startswith("Unnamed")
    ]

    lookup = {c.lower(): c for c in columns}
    selected = lookup.get(requested_sensor.lower())
    if selected is None:
        raise ValueError(
            f"Sensor column '{requested_sensor}' was not found.\nAvailable columns:\n"
            + ", ".join(columns)
        )

    timestamps = pd.to_datetime(
        frame["date"].astype(str) + " " + frame["time"].astype(str),
        format="%d-%b-%y %H:%M:%S",
        errors="coerce",
    )
    values_f = pd.to_numeric(frame[selected], errors="coerce")
    usable = pd.DataFrame(
        {"source_timestamp": timestamps, "temperature_f": values_f}
    ).dropna()

    if usable.empty:
        raise ValueError(f"No usable readings were found for {selected}.")

    # The CSV metadata row explicitly labels thermocouple readings as Fahrenheit.
    # Conversion is performed before any scenario or threshold logic.
    usable["temperature_c"] = (usable["temperature_f"] - 32.0) * 5.0 / 9.0
    return selected, usable.reset_index(drop=True)


def make_event(
    sensor_name: str,
    row: Any,
    profile: VaccineProfile,
    scenario: str,
    *,
    event_number: int,
    total_events: int,
) -> dict[str, Any]:
    """Build one portable JSON event with source and simulation provenance."""
    source_temperature_c = float(row["temperature_c"])
    temperature_c = transform_temperature(
        source_temperature_c,
        profile,
        scenario,
        event_number,
        total_events,
    )
    event = {
        "device_id": "vaccine_temperature_simulator",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_timestamp": row["source_timestamp"].isoformat(),
        "sensor_name": sensor_name,
        "vaccine_type": profile.name,
        "scenario": scenario,
        "temperature_c": round(temperature_c, 2),
        "status": classify_temperature(temperature_c, profile),
    }
    event.update(
        classify_uncertainty(
            event["temperature_c"],
            profile.min_c,
            profile.max_c,
            SENSOR_TOLERANCE_C,
        )
    )
    return event


def main() -> int:
    """Run the replay loop until the event limit is reached or Ctrl+C is pressed."""
    args = parse_arguments()
    try:
        profile = resolve_profile(
            args.vaccine_type,
            min_temp=args.min_temp,
            max_temp=args.max_temp,
        )
        sensor_name, readings = load_temperature_data(Path(args.csv_file), args.sensor)
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Make sure Mosquitto is running on localhost:1883.", file=sys.stderr)
        return 1

    print(f"Sensor: {sensor_name}")
    print(f"Vaccine profile: {profile.name}")
    print(f"Scenario: {args.scenario}")
    print(f"Temperature range: {profile.min_c}°C to {profile.max_c}°C")
    print(f"Usable readings: {len(readings)}")
    print(f"Publishing to {MQTT_TOPIC}")
    print("Press Ctrl+C to stop.\n")

    # Reuse source rows cyclically when max-events is larger than the dataset.
    count = 0
    index = 0
    try:
        while args.max_events == 0 or count < args.max_events:
            event = make_event(
                sensor_name,
                readings.iloc[index],
                profile,
                args.scenario,
                event_number=count + 1,
                total_events=args.max_events,
            )
            result = client.publish(MQTT_TOPIC, json.dumps(event), qos=0)
            result.wait_for_publish()

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("Published:")
                print(json.dumps(event, indent=2))
                print()
            else:
                print(f"Publish failed with MQTT result code {result.rc}.")

            count += 1
            index = (index + 1) % len(readings)
            if args.max_events == 0 or count < args.max_events:
                time.sleep(args.interval_ms / 1000.0)
    except KeyboardInterrupt:
        print("\nStopping temperature event generator.")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
