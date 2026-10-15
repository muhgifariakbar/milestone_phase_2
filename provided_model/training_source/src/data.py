"""Reproducible fictional banking history and SQLite storage."""

import argparse
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np


SCHEMA = """
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    demo_token TEXT NOT NULL UNIQUE
);
CREATE TABLE monthly_balances (
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    month TEXT NOT NULL,
    closing_balance_idr INTEGER NOT NULL CHECK (closing_balance_idr >= 0),
    PRIMARY KEY (customer_id, month)
);
CREATE TABLE features (
    customer_id TEXT PRIMARY KEY REFERENCES customers(customer_id),
    as_of_date TEXT NOT NULL,
    average_balance_36m REAL NOT NULL,
    balance_volatility REAL NOT NULL,
    on_time_payment_rate REAL NOT NULL,
    late_payment_count_36m INTEGER NOT NULL,
    overdraft_count_36m INTEGER NOT NULL,
    inflow_stability REAL NOT NULL,
    missed_payment_next_12m INTEGER NOT NULL CHECK (missed_payment_next_12m IN (0,1))
);
CREATE TABLE assessments (
    customer_id TEXT PRIMARY KEY REFERENCES customers(customer_id),
    as_of_date TEXT NOT NULL,
    model_version TEXT NOT NULL,
    risk_probability REAL NOT NULL,
    score INTEGER NOT NULL,
    tier TEXT NOT NULL,
    credit_limit_idr INTEGER NOT NULL,
    reason_codes_json TEXT NOT NULL
);
"""


@contextmanager
def connect(path: Path, readonly: bool = False) -> Iterator[sqlite3.Connection]:
    if readonly:
        db = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        if not readonly:
            db.commit()
    except Exception:
        if not readonly:
            db.rollback()
        raise
    finally:
        db.close()


def seed(path: Path, *, count: int = 2400, seed_value: int = 20260927) -> None:
    """Generate a single as-of snapshot and a future outcome without feature leakage."""
    if count < 100:
        raise ValueError("at least 100 customers are required")
    rng = np.random.default_rng(seed_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with connect(path) as db:
        db.executescript(SCHEMA)
        months = [f"{year}-{month:02d}" for year in (2023, 2024, 2025) for month in range(1, 13)]
        for index in range(count):
            customer_id = f"C{index + 1:05d}"
            token = f"classroom-token-{index + 1:05d}"
            name = f"Demo Customer {index + 1:05d}"
            base = float(rng.lognormal(np.log(8_000_000), 0.8))
            volatility = float(rng.uniform(0.05, 0.65))
            balances = np.maximum(
                0, base * (1 + rng.normal(0, volatility, 36))
            ).round().astype(int)
            on_time = float(rng.beta(7, 2))
            late = int(rng.poisson(max(0.1, (1 - on_time) * 6)))
            overdrafts = int(rng.poisson(max(0.05, volatility * 3 - 0.4)))
            inflow = float(rng.beta(5, 2))
            avg = float(np.mean(balances))
            observed_volatility = float(np.std(balances) / max(avg, 1))
            # Future label uses a latent risk rule plus fresh randomness; no future field is a feature.
            logit = (
                -2.2 + 0.45 * late + 0.40 * overdrafts
                + 1.7 * (1 - on_time) + 0.9 * observed_volatility
                + 0.6 * (1 - inflow) - 0.20 * np.log1p(avg / 5_000_000)
            )
            probability = 1 / (1 + np.exp(-logit))
            outcome = int(rng.binomial(1, probability))
            db.execute("INSERT INTO customers VALUES (?,?,?)", (customer_id, name, token))
            db.executemany(
                "INSERT INTO monthly_balances VALUES (?,?,?)",
                [(customer_id, month, int(balance)) for month, balance in zip(months, balances)],
            )
            db.execute(
                "INSERT INTO features VALUES (?,?,?,?,?,?,?,?,?)",
                (customer_id, "2025-12-31", avg, observed_volatility, on_time,
                 late, overdrafts, inflow, outcome),
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("artifacts/bank.db"))
    parser.add_argument("--count", type=int, default=2400)
    args = parser.parse_args()
    seed(args.db, count=args.count)
    print(f"Created {args.count} fictional customers in {args.db}")


if __name__ == "__main__":
    main()
