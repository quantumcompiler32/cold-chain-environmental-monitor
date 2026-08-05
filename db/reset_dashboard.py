#!/usr/bin/env python3
"""Reset the open dashboard view without deleting stored PostgreSQL events."""

from __future__ import annotations

import os

import psycopg


DASHBOARD_RESET_CHANNEL = "cold_chain_reset"


def settings() -> dict[str, object]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres")),
        **({"password": os.environ["POSTGRES_PASSWORD"]} if os.environ.get("POSTGRES_PASSWORD") else {}),
    }


def main() -> int:
    environment = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    if environment not in {"development", "dev", "demo", "test"}:
        raise SystemExit("Refusing dashboard reset: APP_ENV/ENVIRONMENT must be development, demo, test, or dev.")

    target = settings()
    if str(target["host"]).lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Refusing dashboard reset against a non-local PostgreSQL host.")

    with psycopg.connect(**target) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_notify(%s, %s)", (DASHBOARD_RESET_CHANNEL, "dashboard_reset"))

    print("Dashboard analytics reset requested. Stored PostgreSQL events were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
