#!/usr/bin/env python3
"""Run read-only latest-event and count checks before opening the dashboard."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import psycopg


ROOT = Path(__file__).resolve().parents[1]
LATEST_SQL = (ROOT / "database" / "verification" / "latest_events.sql").read_text()
LATEST_QUERY, SUMMARY_QUERY = LATEST_SQL.split("\n\nSELECT\n", 1)
SUMMARY_QUERY = "SELECT\n" + SUMMARY_QUERY


def settings() -> dict[str, object]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres")),
        **({"password": os.environ["POSTGRES_PASSWORD"]} if os.environ.get("POSTGRES_PASSWORD") else {}),
    }


def serializable(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def main() -> int:
    target = settings()
    print(f"Verification target: host={target['host']} port={target['port']} database={target['dbname']}")
    with psycopg.connect(**target) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.execute(LATEST_QUERY)
            columns = [column.name for column in cursor.description]
            rows = [dict(zip(columns, (serializable(value) for value in row))) for row in cursor.fetchall()]
            cursor.execute(SUMMARY_QUERY)
            summary_columns = [column.name for column in cursor.description]
            summary_row = cursor.fetchone()
            summary = dict(zip(summary_columns, (serializable(value) for value in summary_row)))
    print(json.dumps({"latest_events": rows, "summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
