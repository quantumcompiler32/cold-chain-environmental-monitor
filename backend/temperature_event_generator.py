#!/usr/bin/env python3
"""Replay CSV temperature readings as scenario-labeled MQTT events.

High-school version: this is a pretend sensor. It reads old measurements from
a spreadsheet, changes them for a chosen experiment, packages each one as
JSON, and mails that message to MQTT.

The generator is the simulation side of the pipeline. It reads one or more
sensor columns from the source CSV, converts Fahrenheit to Celsius, applies
the requested scenario, classifies the resulting temperature, and publishes
JSON events to the shared MQTT topic.
"""

from __future__ import annotations

import argparse
# argparse reads options such as --sensor from the Terminal command.
import json
# json turns each simulated reading into a message MQTT can carry.
import sys
# sys lets us print user-friendly failures to stderr.
import time
import random
from collections import Counter
from uuid import uuid4
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
# paho-mqtt is the messenger that publishes events to Mosquitto.
import paho.mqtt.client as mqtt

from domain_rules import derive_operational_state, normalize_occupancy
from temperature_uncertainty import SENSOR_TOLERANCE_C, classify_uncertainty
from event_contract import format_timestamp, now_utc, parse_timestamp
from terminal_output import format_event_block, format_service_message


# The local Mosquitto broker and topic shared with temperature_subscriber.py.
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "devices/temperature"

DEFAULT_SENSOR = "Pod1"
DEFAULT_INTERVAL_MS = 2000
# The source file is a Pfizer ultralow experiment. Keep its small variations
# while translating the baseline around the selected profile's target.
SOURCE_PROFILE_TARGET_C = -78.5
STABLE_TOLERANCE_C = 1.0
OUTLIER_OFFSET_C = 1.0
FAILURE_OFFSET_C = 5.0
SCENARIOS = ("normal", "warning", "recovery", "mixed", "outlier")


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
    # A custom storage range needs both ends; one limit alone is incomplete.
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


def normalize_sensor_names(sensor_values: list[str]) -> list[str]:
    """Expand repeated/comma-separated sensor arguments without duplicates."""
    names: list[str] = []
    seen: set[str] = set()
    for value in sensor_values:
        for candidate in value.split(","):
            name = candidate.strip()
            if not name:
                continue
            key = name.casefold()
            if key not in seen:
                names.append(name)
                seen.add(key)
    if not names:
        raise ValueError("Provide at least one Pod after --sensor.")
    return names


def parse_arguments() -> argparse.Namespace:
    """Read the command-line controls used to build the simulation."""
    # argparse converts Terminal text such as --max-events 20 into Python
    # values that the rest of the program can use.
    parser = argparse.ArgumentParser(
        description="Generate vaccine temperature events and publish them to MQTT."
    )
    parser.add_argument(
        "--sensor",
        nargs="+",
        default=[DEFAULT_SENSOR],
        metavar="POD",
        help=(
            "Pod temperature columns, for example Pod1 Pod2 Pod3; "
            f"comma-separated values also work (default: {DEFAULT_SENSOR})."
        ),
    )
    parser.add_argument(
        "--csv-file",
        default=None,
        help="Optional external CSV file to replay; otherwise use built-in deterministic guidance.",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=DEFAULT_INTERVAL_MS,
        help=f"Milliseconds between events (default: {DEFAULT_INTERVAL_MS}).",
    )
    parser.add_argument(
        "--count", "--max-events",
        dest="count",
        type=int,
        default=0,
        help="Maximum events to publish; 0 means unlimited.",
    )
    parser.add_argument(
        "--vaccine", "--vaccine-type",
        dest="vaccine_type",
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
        "--occupancy-state",
        choices=("loaded", "empty", "offline"),
        default="loaded",
        help="Pod domain state used for alerts and dashboard status.",
    )
    parser.add_argument(
        "--batch-id",
        help="Active batch ID for a loaded pod; defaults to a demo batch per Pod.",
    )
    parser.add_argument(
        "--cooling-enabled",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether the pod cooling system is running (default: enabled).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed scenario/value selection and generated event IDs.",
    )
    parser.add_argument(
        "--output-mode",
        choices=("none", "summary", "verbose"),
        default="summary",
        help="Console output detail (default: summary).",
    )
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="Persist directly through the shared dual-write service; normally the listener owns database writes.",
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

    try:
        args.sensor = normalize_sensor_names(args.sensor)
    except ValueError as exc:
        parser.error(str(exc))
    if args.interval_ms < 0:
        parser.error("--interval-ms cannot be negative.")
    if args.count < 0:
        parser.error("--count cannot be negative.")
    if args.scenario in {"recovery", "mixed"} and args.count == 0:
        parser.error(f"--scenario {args.scenario} requires --count.")
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
    # Check dangerous extremes first, then check whether we are close to the
    # preferred target.
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


def safe_baseline_temperature(source_temperature_c: float, profile: VaccineProfile) -> float:
    """Keep the translated source variation inside the selected safe range."""
    if profile.min_c is None or profile.max_c is None:
        raise ValueError("Temperature bounds are required for a safe baseline.")
    adapted_temperature = adapt_source_temperature(source_temperature_c, profile)
    return min(max(adapted_temperature, profile.min_c), profile.max_c)


def transform_temperature(
    source_temperature_c: float,
    profile: VaccineProfile,
    scenario: str,
    event_number: int,
    total_events: int,
) -> float:
    """Apply deterministic scenario behavior to one source reading.

    Normal preserves the source variation while staying inside the selected
    profile range. Outlier makes every reading an intentional exception,
    failure holds a sustained warm excursion, and recovery interpolates from
    failure back to the profile target across the requested event count.
    """
    # Every scenario needs a complete safe range to compare against.
    if profile.min_c is None or profile.max_c is None:
        raise ValueError("Temperature bounds are required for scenarios.")
    if event_number <= 0:
        raise ValueError("event_number must be positive.")

    if scenario == "normal":
        # Baseline simulation: preserve the source variation around the
        # selected vaccine profile without allowing a source excursion to
        # create an incident in the normal test scenario.
        return safe_baseline_temperature(source_temperature_c, profile)
    if scenario == "warning":
        # Stay inside the documented range while the sensor's ±0.5°C
        # uncertainty interval crosses the warm boundary.
        return profile.max_c - 0.25
    if scenario == "outlier":
        # Every event is intentionally outside the safe range. Alternating the
        # direction gives the analysis report both cold and warm examples.
        if event_number % 2 == 1:
            return profile.min_c - OUTLIER_OFFSET_C
        return profile.max_c + OUTLIER_OFFSET_C
    if scenario in {"failure", "cooling_failure"}:
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
    if scenario == "mixed":
        if total_events <= 0:
            raise ValueError("Mixed requires a positive total event count.")
        normal_end = max(1, total_events // 3)
        failure_end = max(normal_end + 1, (total_events * 2) // 3)
        if event_number <= normal_end:
            return safe_baseline_temperature(source_temperature_c, profile)
        if event_number <= failure_end:
            return profile.max_c + FAILURE_OFFSET_C
        recovery_number = event_number - failure_end
        recovery_total = total_events - failure_end
        progress = (recovery_number - 1) / max(recovery_total - 1, 1)
        failure_temperature = profile.max_c + FAILURE_OFFSET_C
        return failure_temperature + (
            profile.target_c - failure_temperature
        ) * progress
    raise ValueError(f"Unknown scenario: {scenario}")


def built_in_temperature_data(requested_sensor: str):
    """Return small deterministic guidance so the demo needs no raw CSV."""
    temperatures_c = [-78.7, -78.5, -78.3, -78.4, -78.6]
    temperatures_f = [(value * 9.0 / 5.0) + 32.0 for value in temperatures_c]
    return requested_sensor, pd.DataFrame({
        "temperature_f": temperatures_f,
        "temperature_c": temperatures_c,
    })


def load_temperature_data(csv_path: Path | None, requested_sensor: str):
    """Load one sensor column and return usable timestamps and Celsius values."""
    if csv_path is None:
        return built_in_temperature_data(requested_sensor)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path.resolve()}\n"
            "Provide a valid external file with --csv-file or omit that option to use built-in guidance."
        )

    # pandas loads the CSV into a table so we can select a sensor column by
    # name and clean invalid cells.
    frame = pd.read_csv(csv_path, low_memory=False)
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

    values_f = pd.to_numeric(frame[selected], errors="coerce")
    usable = pd.DataFrame({"temperature_f": values_f}).dropna()

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
    event_id: str | None = None,
    event_time: datetime | None = None,
    occupancy_state: str = "loaded",
    batch_id: str | None = None,
    cooling_enabled: bool = True,
) -> dict[str, Any]:
    """Build one portable JSON event representing a newly generated reading."""
    # The CSV supplies temperature shape only; this event is created now.
    source_temperature_c = float(row["temperature_c"])
    temperature_c = transform_temperature(
        source_temperature_c,
        profile,
        scenario,
        event_number,
        total_events,
    )
    # Build the common envelope shared by the generator, subscriber, and UI.
    generated_event_time = now_utc(lambda: event_time) if event_time is not None else now_utc()
    event = {
        "event_id": event_id or str(uuid4()),
        "device_id": "vaccine_temperature_simulator",
        "event_time": format_timestamp(generated_event_time),
        # Legacy aliases remain on the wire while consumers migrate.
        "timestamp": format_timestamp(generated_event_time),
        "sensor_name": sensor_name,
        "vaccine_type": profile.name,
        "scenario": scenario,
        "occupancy_state": normalize_occupancy(occupancy_state),
        "batch_id": batch_id,
        "cooling_enabled": cooling_enabled,
        "temperature_c": round(temperature_c, 2),
        "status": classify_temperature(temperature_c, profile),
    }
    if scenario == "mixed":
        normal_end = max(1, total_events // 3)
        failure_end = max(normal_end + 1, (total_events * 2) // 3)
        event["scenario_phase"] = (
            "normal" if event_number <= normal_end
            else "cooling_failure" if event_number <= failure_end
            else "recovery"
        )
    # Add the possible sensor range without changing the measured temperature.
    event.update(
        classify_uncertainty(
            event["temperature_c"],
            profile.min_c,
            profile.max_c,
            SENSOR_TOLERANCE_C,
        )
    )
    event.update(derive_operational_state(event))
    return event


def main() -> int:
    """Run the replay loop until the event limit is reached or Ctrl+C is pressed."""
    # This is the starting point when the file is run from Terminal.
    args = parse_arguments()
    try:
        profile = resolve_profile(
            args.vaccine_type,
            min_temp=args.min_temp,
            max_temp=args.max_temp,
        )
        rng = random.Random(args.seed)
        sensor_runs = []
        for requested_sensor in args.sensor:
            sensor_name, readings = load_temperature_data(
                Path(args.csv_file) if args.csv_file else None,
                requested_sensor,
            )
            sensor_runs.append({
                "sensor_name": sensor_name,
                "readings": readings,
                "index": rng.randrange(len(readings)) if args.seed is not None else 0,
            })
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Make sure Mosquitto is running on localhost:1883.", file=sys.stderr)
        return 1

    if args.output_mode == "verbose":
        sensor_list = ", ".join(run["sensor_name"] for run in sensor_runs)
        readings_list = ", ".join(
            f'{run["sensor_name"]}:{len(run["readings"])}'
            for run in sensor_runs
        )
        print(format_service_message("GENERATOR", f"sensors={sensor_list}; vaccine={profile.name}; scenario={args.scenario}"), flush=True)
        print(format_service_message("GENERATOR", f"temperature_range={profile.min_c}°C to {profile.max_c}°C; usable_readings={readings_list}"), flush=True)
        print(format_service_message("GENERATOR", f"publishing_to={MQTT_TOPIC}; seed={args.seed}; interval_ms={args.interval_ms}; occupancy={args.occupancy_state}"), flush=True)
        print(format_service_message("GENERATOR", "Press Control-C to stop."), flush=True)

    # Reuse source rows cyclically when max-events is larger than the dataset.
    # That lets a short CSV produce a long controlled experiment.
    count = 0
    published = 0
    failed = 0
    scenario_counts = Counter()
    phase_counts = Counter()
    first_event_time = None
    last_event_time = None
    started = time.perf_counter()
    batch_ids = {
        run["sensor_name"]: args.batch_id or (
            f'{run["sensor_name"]}-DEMO-BATCH'
            if args.occupancy_state == "loaded" else None
        )
        for run in sensor_runs
    }
    per_sensor_published = Counter()
    per_sensor_failed = Counter()
    direct_persist = None
    if args.write_db:
        try:
            from temperature_subscriber import persist_event
            direct_persist = persist_event
        except ImportError:  # pragma: no cover
            from temperature_subscriber import persist_event
    try:
        while args.count == 0 or count < args.count:
            # Each loop is one round: publish one event for every selected Pod
            # before waiting for the requested interval.
            for run in sensor_runs:
                sensor_name = run["sensor_name"]
                event = make_event(
                    sensor_name,
                    run["readings"].iloc[run["index"]],
                    profile,
                    args.scenario,
                    event_number=count + 1,
                    total_events=args.count,
                    event_id=str(UUID(int=rng.getrandbits(128))) if args.seed is not None else None,
                    occupancy_state=args.occupancy_state,
                    batch_id=batch_ids[sensor_name],
                    cooling_enabled=args.cooling_enabled,
                )
                # Keep the requested scenario separate from the optional phase.
                # This prevents a mixed run from being reported as if its phases
                # were three different top-level scenarios.
                scenario_counts[event["scenario"]] += 1
                phase_counts[event.get("scenario_phase", event["scenario"])] += 1
                event_time = parse_timestamp(event["event_time"], "event_time", assume_utc=False)
                first_event_time = first_event_time or event_time
                last_event_time = event_time
                # Publish without waiting for a reply from the subscriber.
                result = client.publish(MQTT_TOPIC, json.dumps(event), qos=0)
                result.wait_for_publish()

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    published += 1
                    per_sensor_published[sensor_name] += 1
                    write_result = None
                    if direct_persist is not None:
                        write_result = direct_persist(event, topic=MQTT_TOPIC)
                    if args.output_mode == "verbose":
                        outcome = "PUBLISHED"
                        if write_result is not None:
                            outcome += " + DUPLICATE" if write_result.duplicate else " + DB STORED"
                        print(format_event_block(
                            event,
                            component="GENERATOR",
                            outcome=outcome,
                            sequence=count + 1,
                            topic=MQTT_TOPIC,
                            stored_at=write_result.stored_at if write_result is not None else None,
                        ), flush=True)
                else:
                    failed += 1
                    per_sensor_failed[sensor_name] += 1
                    if args.output_mode != "none":
                        print(format_service_message("GENERATOR", f"PUBLISH FAILED {sensor_name} round #{count + 1:04d}; mqtt_code={result.rc}"), file=sys.stderr, flush=True)

                run["index"] = (run["index"] + 1) % len(run["readings"])

            count += 1
            if args.count == 0 or count < args.count:
                time.sleep(args.interval_ms / 1000.0)
    except KeyboardInterrupt:
        if args.output_mode != "none":
            print("\n" + format_service_message("GENERATOR", "Stopping temperature event generator."), flush=True)
    finally:
        client.loop_stop()
        client.disconnect()
    elapsed = max(time.perf_counter() - started, 1e-9)
    if args.output_mode == "summary":
        print(json.dumps({
            "pods": [run["sensor_name"] for run in sensor_runs],
            "requested": args.count if args.count else "unlimited",
            "requested_per_pod": args.count if args.count else "unlimited",
            "rounds": count,
            "generated": count * len(sensor_runs),
            "published": published,
            "failed": failed,
            "per_pod": {
                sensor_name: {
                    "published": per_sensor_published[sensor_name],
                    "failed": per_sensor_failed[sensor_name],
                }
                for sensor_name in (run["sensor_name"] for run in sensor_runs)
            },
            "per_scenario": dict(sorted(scenario_counts.items())),
            "per_phase": dict(sorted(phase_counts.items())),
            "first_event_time": format_timestamp(first_event_time) if first_event_time else None,
            "last_event_time": format_timestamp(last_event_time) if last_event_time else None,
            "elapsed_seconds": round(elapsed, 3),
            "events_per_second": round(count / elapsed, 3),
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
