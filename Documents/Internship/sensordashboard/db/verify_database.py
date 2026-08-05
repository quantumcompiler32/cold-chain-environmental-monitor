#!/usr/bin/env python3
"""Run a fast, read-only database and projection-parity check.

This is intentionally smaller than verify_persistence.py: it does one schema
check and one indexed aggregate query, then emits one JSON diagnostic suitable
for a terminal probe or CI step.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime, time as datetime_time
from decimal import Decimal
from uuid import UUID

import psycopg


def settings() -> dict[str, object]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres")),
        **({"password": os.environ["POSTGRES_PASSWORD"]} if os.environ.get("POSTGRES_PASSWORD") else {}),
    }


def serializable(value):
    if isinstance(value, (datetime, date, datetime_time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


SCHEMA_QUERY = """
SELECT
    to_regclass('public.telemetry_logs') AS telemetry_logs,
    to_regclass('public.vaccine_temperature_events') AS vaccine_temperature_events,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'telemetry_logs' AND column_name = 'run_id'
    ) AS telemetry_run_id,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'vaccine_temperature_events' AND column_name = 'run_id'
    ) AS vaccine_run_id
"""

PARITY_QUERY = """
SELECT
    (SELECT COUNT(*) FROM telemetry_logs) AS generic_count,
    (SELECT COUNT(*) FROM vaccine_temperature_events) AS domain_count,
    (SELECT COUNT(*) FROM telemetry_logs raw
       LEFT JOIN vaccine_temperature_events domain USING (event_id)
       WHERE domain.event_id IS NULL) AS orphan_generic_count,
    (SELECT COUNT(*) FROM vaccine_temperature_events domain
       LEFT JOIN telemetry_logs raw USING (event_id)
       WHERE raw.event_id IS NULL) AS orphan_domain_count,
    (SELECT event_id FROM vaccine_temperature_events ORDER BY event_time DESC, event_id DESC LIMIT 1) AS latest_event_id,
    (SELECT run_id FROM vaccine_temperature_events ORDER BY event_time DESC, event_id DESC LIMIT 1) AS latest_run_id,
    (SELECT event_time FROM vaccine_temperature_events ORDER BY event_time DESC, event_id DESC LIMIT 1) AS latest_event_time
"""


def main() -> int:
    started = time.perf_counter()
    target = settings()
    try:
        with psycopg.connect(**target) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET TIME ZONE 'UTC'")
                cursor.execute(SCHEMA_QUERY)
                schema_columns = [column.name for column in cursor.description]
                schema_row = dict(zip(schema_columns, cursor.fetchone()))
                missing = [name for name, value in schema_row.items() if not value]
                if missing:
                    result = {
                        "ok": False,
                        "ready": False,
                        "database_connected": True,
                        "read_only": True,
                        "missing_tables": missing,
                    }
                else:
                    cursor.execute(PARITY_QUERY)
                    columns = [column.name for column in cursor.description]
                    values = [serializable(value) for value in cursor.fetchone()]
                    result = {
                        "ok": True,
                        "ready": True,
                        "database_connected": True,
                        "read_only": True,
                        **dict(zip(columns, values)),
                    }
    except (psycopg.Error, OSError, ValueError) as exc:
        result = {
            "ok": False,
            "ready": False,
            "database_connected": False,
            "read_only": True,
            "error": str(exc),
        }

    if result.get("ready"):
        result["ok"] = (
            result["generic_count"] == result["domain_count"]
            and result["orphan_generic_count"] == 0
            and result["orphan_domain_count"] == 0
        )
        if not result["ok"]:
            result["error"] = "generic and vaccine projections are not in parity"
    result["target"] = {key: value for key, value in target.items() if key != "password"}
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
