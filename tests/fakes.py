"""Small MongoDB-like fixture for public API contract checks."""


class Collection:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def find(self, query: dict, projection: dict | None = None):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                yield dict(row)

    def find_one(self, query: dict, projection: dict | None = None):
        return next(self.find(query, projection), None)


def example_database(*, incomplete: bool = False) -> dict:
    months = [f"{year}-{month:02d}" for year in (2023, 2024, 2025)
              for month in range(1, 13)]
    if incomplete:
        months = months[1:]
    features = {"average_balance_36m": 8_000_000, "balance_volatility": 0.1,
                "on_time_payment_rate": 0.9, "late_payment_count_36m": 0,
                "overdraft_count_36m": 0, "inflow_stability": 0.8}
    return {
        "demo_identities": Collection([
            {"customer_id": "C90001", "demo_token": "public-token-a", "display_name": "Alex"},
            {"customer_id": "C90002", "demo_token": "public-token-b", "display_name": "Blair"},
        ]),
        "customer_assessments": Collection([
            {"customer_id": "C90001", "status": "available", "as_of_date": "2025-12-31",
             "model_version": "synthetic-cart-v2", "features": features,
             "average_balance_36m": 8_000_000, "risk_probability": 0.2,
             "score": 740, "tier": "lower risk", "credit_limit_idr": 12_000_000,
             "reason_codes": [{"feature": "on_time_payment_rate",
                               "observed_value": 0.9, "threshold": 0.7,
                               "direction": "lower risk", "path_risk_change": -0.1,
                               "description": "Recorded on-time payment path"}],
             "customer_note": ""},
        ]),
        "monthly_balances": Collection([
            {"customer_id": "C90001", "month": month, "closing_balance_idr": 8_000_000}
            for month in months
        ]),
    }
