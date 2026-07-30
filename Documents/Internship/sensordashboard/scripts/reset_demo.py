#!/usr/bin/env python3
"""Safely reset and rebuild application tables for development/demo use."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESET_SQL = (PROJECT_ROOT / "database" / "reset" / "reset_demo.sql").read_text()
BOOTSTRAP_SQL = (PROJECT_ROOT / "database" / "bootstrap" / "001_core.sql").read_text()


def settings() -> dict[str, object]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "iotdb"),
        "user": os.environ.get("POSTGRES_USER", os.environ.get("USER", "postgres")),
        **({"password": os.environ["POSTGRES_PASSWORD"]} if os.environ.get("POSTGRES_PASSWORD") else {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset and rebuild local/demo application tables.")
    parser.add_argument("--confirm-reset", action="store_true", help="Explicitly authorize deleting application tables.")
    args = parser.parse_args()
    environment = os.environ.get("APP_ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    if environment not in {"development", "dev", "demo", "test"}:
        parser.error("Refusing to reset: APP_ENV/ENVIRONMENT must be development, demo, test, or dev.")
    if not args.confirm_reset:
        parser.error("Refusing to reset: pass --confirm-reset explicitly.")

    target = settings()
    if str(target["host"]).lower() not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Refusing to reset a non-local PostgreSQL host.")
    print(f"Reset target: host={target['host']} port={target['port']} database={target['dbname']} environment={environment}")
    with psycopg.connect(**target) as connection:
        with connection.cursor() as cursor:
            cursor.execute(RESET_SQL)
            cursor.execute(BOOTSTRAP_SQL)
            # Tell already-open dashboard streams that their in-memory
            # analytics must be cleared for the next isolated demo run.
            cursor.execute("SELECT pg_notify(%s, %s)", ("cold_chain_reset", "demo_reset"))
    print("Application tables and indexes recreated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
