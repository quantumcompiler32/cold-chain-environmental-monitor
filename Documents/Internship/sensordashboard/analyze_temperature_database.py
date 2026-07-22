#!/usr/bin/env python3
"""Run readable, read-only questions against the temperature_events table.

The report is deliberately separate from event generation: the generator
assigns the status and provenance, while this program summarizes what was
stored. It prints overall statistics, provenance by scenario, status
percentages, sensor comparisons, and the coldest and warmest readings.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from typing import Any, Callable

import psycopg


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "iotdb")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mokshjoshi")


def connect_database() -> psycopg.Connection[Any]:
    """Connect using the same local defaults as the subscriber."""
    # Environment variables make the copied folder portable to another
    # developer without changing the source files.
    connection_options: dict[str, Any] = {
        "host": POSTGRES_HOST,
        "port": POSTGRES_PORT,
        "dbname": POSTGRES_DB,
        "user": POSTGRES_USER,
    }
    password = os.getenv("POSTGRES_PASSWORD")
    if password:
        connection_options["password"] = password
    return psycopg.connect(**connection_options)


def format_value(value: Any) -> str:
    """Make database values easy to read in a terminal."""
    if value is None:
        return "N/A"
    if isinstance(value, (float, Decimal)):
        return f"{float(value):.2f}"
    return str(value)


def print_table(
    title: str,
    headers: list[str],
    rows: list[tuple[Any, ...]],
    printer: Callable[[str], None],
) -> None:
    """Print a small aligned table without requiring another package."""
    # Calculate widths first so the report stays readable in a plain terminal.
    printer(f"\n{title}")
    if not rows:
        printer("No data found.")
        return

    formatted_rows = [[format_value(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in formatted_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    printer(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    printer("-+-".join("-" * width for width in widths))
    for row in formatted_rows:
        printer(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def run_analysis(
    connection: psycopg.Connection[Any],
    *,
    limit: int = 5,
    printer: Callable[[str], None] = print,
) -> None:
    """Run the report's questions and print human-readable answers.

    ``limit`` only controls how many coldest and warmest rows are displayed;
    it does not limit the totals, percentages, or grouped summaries.
    """
    with connection.cursor() as cursor:
        # First answer the overall data-quality questions for the entire table.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_events,
                COUNT(DISTINCT sensor_name) AS total_sensors,
                MIN(source_timestamp) AS first_measurement,
                MAX(source_timestamp) AS last_measurement,
                ROUND(MIN(temperature_c)::numeric, 2) AS minimum_temperature,
                ROUND(MAX(temperature_c)::numeric, 2) AS maximum_temperature,
                ROUND(AVG(temperature_c)::numeric, 2) AS average_temperature,
                ROUND(COALESCE(STDDEV_POP(temperature_c), 0)::numeric, 2)
                    AS temperature_std_dev,
                COUNT(DISTINCT source_timestamp::date) AS days_of_data,
                COUNT(*) - COUNT(temperature_c) AS missing_temperature_values
            FROM temperature_events;
            """
        )
        overview = cursor.fetchone()

        if overview is None or overview[0] == 0:
            printer("\nTEMPERATURE DATABASE SUMMARY")
            printer("No events found in temperature_events.")
            return

        (
            total_events,
            total_sensors,
            first_measurement,
            last_measurement,
            minimum_temperature,
            maximum_temperature,
            average_temperature,
            temperature_std_dev,
            days_of_data,
            missing_temperature_values,
        ) = overview

        printer("\nTEMPERATURE DATABASE SUMMARY")
        printer(f"Total Events: {total_events}")
        printer(f"Total Sensors: {total_sensors}")
        printer(f"First Measurement: {format_value(first_measurement)}")
        printer(f"Last Measurement: {format_value(last_measurement)}")
        printer(f"Minimum Temperature (C): {format_value(minimum_temperature)}")
        printer(f"Maximum Temperature (C): {format_value(maximum_temperature)}")
        printer(f"Average Temperature (C): {format_value(average_temperature)}")
        printer(f"Temperature Std Dev: {format_value(temperature_std_dev)}")
        printer(f"Days of Data: {days_of_data}")
        printer(f"Missing Temperature Values: {missing_temperature_values}")

        # Provenance tells us which vaccine profile and simulation produced rows.
        cursor.execute(
            """
            SELECT vaccine_type, scenario, COUNT(*) AS event_count
            FROM temperature_events
            GROUP BY vaccine_type, scenario
            ORDER BY vaccine_type, scenario;
            """
        )
        provenance_rows = cursor.fetchall()
        print_table(
            "PROVENANCE SUMMARY",
            ["Vaccine Profile", "Scenario", "Events"],
            provenance_rows,
            printer,
        )

        # Status counts show the operational result of the generator's rules.
        cursor.execute(
            """
            SELECT
                status,
                COUNT(*) AS event_count,
                ROUND(
                    100.0 * COUNT(*) /
                    NULLIF((SELECT COUNT(*) FROM temperature_events), 0),
                    2
                ) AS percentage
            FROM temperature_events
            GROUP BY status
            ORDER BY status;
            """
        )
        status_rows = cursor.fetchall()
        print_table(
            "STATUS SUMMARY",
            ["Status", "Events", "Percentage"],
            [(status, count, f"{format_value(percentage)}%") for status, count, percentage in status_rows],
            printer,
        )

        # This report keeps raw status counts separate from the measurement
        # uncertainty interpretation. A borderline reading is not silently
        # converted into TOO_COLD or TOO_WARM.
        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE uncertainty_status LIKE 'BORDERLINE%') AS borderline_count,
                COUNT(*) FILTER (WHERE boundary_crossing) AS crossing_count,
                COUNT(*) FILTER (
                    WHERE ABS(temperature_c - storage_min_c) <= sensor_tolerance_c
                       OR ABS(temperature_c - storage_max_c) <= sensor_tolerance_c
                ) AS near_threshold_count,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE boundary_crossing) /
                    NULLIF(COUNT(*), 0), 2
                ) AS crossing_percentage
            FROM temperature_events;
            """
        )
        borderline_count, crossing_count, near_threshold_count, crossing_percentage = cursor.fetchone()
        printer("\nUNCERTAINTY SUMMARY")
        printer(f"Borderline readings: {borderline_count}")
        printer(f"Readings crossing a storage boundary: {crossing_count}")
        printer(f"Readings near a threshold (+/- sensor tolerance): {near_threshold_count}")
        printer(f"Boundary-crossing percentage: {format_value(crossing_percentage)}%")

        # Grouping by sensor helps compare different source channels.
        cursor.execute(
            """
            SELECT
                sensor_name,
                COUNT(*) AS readings,
                ROUND(MIN(temperature_c)::numeric, 2) AS minimum_temperature,
                ROUND(MAX(temperature_c)::numeric, 2) AS maximum_temperature,
                ROUND(AVG(temperature_c)::numeric, 2) AS average_temperature
            FROM temperature_events
            GROUP BY sensor_name
            ORDER BY sensor_name;
            """
        )
        sensor_rows = cursor.fetchall()
        print_table(
            "ANALYSIS BY SENSOR",
            ["Sensor", "Readings", "Minimum C", "Maximum C", "Average C"],
            sensor_rows,
            printer,
        )

        # These two limited queries keep the report readable while still
        # surfacing the most extreme stored readings.
        cursor.execute(
            """
            SELECT sensor_name, ROUND(temperature_c::numeric, 2), source_timestamp, status
            FROM temperature_events
            ORDER BY temperature_c ASC, source_timestamp ASC
            LIMIT %s;
            """,
            (limit,),
        )
        coldest_rows = cursor.fetchall()
        print_table(
            f"{limit} COLDEST READINGS",
            ["Sensor", "Temperature C", "Source Time", "Status"],
            coldest_rows,
            printer,
        )

        cursor.execute(
            """
            SELECT sensor_name, ROUND(temperature_c::numeric, 2), source_timestamp, status
            FROM temperature_events
            ORDER BY temperature_c DESC, source_timestamp DESC
            LIMIT %s;
            """,
            (limit,),
        )
        warmest_rows = cursor.fetchall()
        print_table(
            f"{limit} WARMEST READINGS",
            ["Sensor", "Temperature C", "Source Time", "Status"],
            warmest_rows,
            printer,
        )


def parse_arguments() -> argparse.Namespace:
    # This report is read-only; the only control is how many extremes to show.
    parser = argparse.ArgumentParser(
        description="Run simple, readable questions against temperature_events."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of coldest and warmest readings to show (default: 5).",
    )
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be greater than zero.")
    return args


def main() -> int:
    # Keep connection errors friendly because PostgreSQL is optional for the
    # browser simulation.
    args = parse_arguments()
    try:
        with connect_database() as connection:
            run_analysis(connection, limit=args.limit)
    except psycopg.errors.UndefinedTable:
        print(
            "ERROR: temperature_events does not exist. "
            "Run: psql -U mokshjoshi -d iotdb -f create_temperature_table.sql",
            file=sys.stderr,
        )
        return 1
    except psycopg.OperationalError as exc:
        print(f"ERROR: PostgreSQL connection failed: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error as exc:
        print(f"ERROR: PostgreSQL query failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
