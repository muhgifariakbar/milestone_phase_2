"""Loads data_training/*.ndjson into the Postgres database named by
MONGODB_URI/MONGODB_DATABASE (names kept as-is -- compose.yaml bakes them
in). Dev/demo tooling only; the graded API never writes to the database.

Usage:
    source .venv/bin/activate
    export MONGODB_URI=postgresql://postgres:postgres@localhost:5432/milestone_2
    export MONGODB_DATABASE=milestone_2
    python scripts/load_data_training.py
"""

import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.postgres_adapter import resolve_dsn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_training"
SCHEMA = ROOT / "scripts" / "schema.sql"

IDENTITY_COLUMNS = ("customer_id", "demo_token", "display_name", "scenario")
ASSESSMENT_COLUMNS = ("customer_id", "status", "as_of_date", "model_version",
                      "risk_probability", "score", "tier", "credit_limit_idr",
                      "average_balance_36m", "features", "reason_codes", "customer_note")
BALANCE_COLUMNS = ("customer_id", "month", "closing_balance_idr")


def _load_ndjson(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _insert(cursor, table: str, columns: tuple[str, ...], rows: list[dict],
            json_columns: frozenset[str] = frozenset()) -> None:
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"  # noqa: S608
    values = []
    for row in rows:
        record = []
        for column in columns:
            value = row.get(column)
            record.append(Jsonb(value) if column in json_columns else value)
        values.append(record)
    cursor.executemany(sql, values)


def main() -> None:
    uri = os.environ["MONGODB_URI"]
    dsn = resolve_dsn(uri, os.getenv("MONGODB_DATABASE"))
    with psycopg.connect(dsn, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA.read_text(encoding="utf-8"))
            for table in ("demo_identities", "customer_assessments", "monthly_balances"):
                cursor.execute(f"TRUNCATE TABLE {table}")  # noqa: S608

            identities = _load_ndjson(DATA / "demo_identities.ndjson")
            _insert(cursor, "demo_identities", IDENTITY_COLUMNS, identities)
            print(f"demo_identities: inserted {len(identities)} rows")

            assessments = _load_ndjson(DATA / "customer_assessments.ndjson")
            _insert(cursor, "customer_assessments", ASSESSMENT_COLUMNS, assessments,
                    json_columns=frozenset({"features", "reason_codes"}))
            print(f"customer_assessments: inserted {len(assessments)} rows")

            balances = _load_ndjson(DATA / "monthly_balances.ndjson")
            for start in range(0, len(balances), 5000):
                _insert(cursor, "monthly_balances", BALANCE_COLUMNS,
                        balances[start:start + 5000])
            print(f"monthly_balances: inserted {len(balances)} rows")
    print("done")


if __name__ == "__main__":
    main()
