"""Participant task: identity-bound, read-only MongoDB queries."""

from decimal import Decimal, ROUND_DOWN

EXPECTED_MONTHS = frozenset(
    f"{year}-{month:02d}" for year in (2023, 2024, 2025) for month in range(1, 13)
)
MODEL_VERSION = "synthetic-cart-v2"
KNOWN_FEATURES = frozenset({
    "average_balance_36m",
    "balance_volatility",
    "on_time_payment_rate",
    "late_payment_count_36m",
    "overdraft_count_36m",
    "inflow_stability",
})
REASON_CODE_KEYS = frozenset({
    "feature", "observed_value", "threshold", "direction", "path_risk_change", "description",
})
# Published policy bands (brief.md / provided_model/training_source/src/policy.py).
SCORE_BANDS = (
    (550, "higher risk", Decimal("0.5")),
    (650, "moderate risk", Decimal("1.0")),
    (750, "lower risk", Decimal("1.5")),
    (851, "lowest risk", Decimal("2.0")),
)
LIMIT_CAP = Decimal("100000000")
ROUND_UNIT = Decimal("100000")


class RepositoryUnavailable(Exception):
    """Raised only for a connection/query-level Mongo failure, never a clean 'not found'."""


def _score_band(score: int) -> tuple[str, Decimal] | None:
    if not isinstance(score, int) or not 300 <= score <= 850:
        return None
    for upper, label, multiplier in SCORE_BANDS:
        if score < upper:
            return label, multiplier
    return None


def _expected_limit(mean: float, multiplier: Decimal) -> int:
    raw = min(Decimal(str(mean)) * multiplier, LIMIT_CAP)
    return int((raw / ROUND_UNIT).to_integral_value(rounding=ROUND_DOWN) * ROUND_UNIT)


def _valid_reason_codes(reason_codes) -> bool:
    if not isinstance(reason_codes, list) or not 1 <= len(reason_codes) <= 3:
        return False
    for entry in reason_codes:
        if not isinstance(entry, dict):
            return False
        if not REASON_CODE_KEYS.issubset(entry.keys()):
            return False
        if entry["feature"] not in KNOWN_FEATURES:
            return False
    return True


class Repository:
    def __init__(self, database):
        self.database = database

    def _find_one(self, collection: str, query: dict) -> dict | None:
        try:
            return self.database[collection].find_one(query)
        except Exception as exc:
            raise RepositoryUnavailable(f"{collection} lookup failed") from exc

    def _find(self, collection: str, query: dict) -> list[dict]:
        try:
            return list(self.database[collection].find(query))
        except Exception as exc:
            raise RepositoryUnavailable(f"{collection} query failed") from exc

    def customer_for_token(self, token: str) -> dict | None:
        if not token:
            return None
        return self._find_one("demo_identities", {"demo_token": token})

    def _balance_history(self, customer_id: str) -> tuple[float, int] | None:
        rows = self._find("monthly_balances", {"customer_id": customer_id})
        if len(rows) != 36:
            return None
        months = {row.get("month") for row in rows}
        if months != EXPECTED_MONTHS:
            return None
        balances = [row.get("closing_balance_idr") for row in rows]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                   for value in balances):
            return None
        return sum(balances) / 36, 36

    def balance_summary(self, customer_id: str) -> dict | None:
        history = self._balance_history(customer_id)
        if history is None:
            return None
        mean, count = history
        return {"average_balance_36m": mean, "month_count": count}

    def assessment(self, customer_id: str) -> dict | None:
        doc = self._find_one("customer_assessments", {"customer_id": customer_id})
        if doc is None:
            return None

        history = self._balance_history(customer_id)
        if history is None:
            return None
        mean, _ = history

        if doc.get("model_version") != MODEL_VERSION:
            return None

        score = doc.get("score")
        risk_probability = doc.get("risk_probability")
        if isinstance(risk_probability, (int, float)) and not isinstance(risk_probability, bool):
            expected_score = min(850, max(300, round(850 - 550 * risk_probability)))
            if expected_score != score:
                return None

        stored_mean = doc.get("average_balance_36m")
        if not isinstance(stored_mean, (int, float)) or isinstance(stored_mean, bool):
            return None
        if abs(mean - stored_mean) > 1:
            return None

        band = _score_band(score)
        if band is None:
            return None
        tier_label, multiplier = band
        stored_tier = doc.get("tier")
        if stored_tier is not None and stored_tier != tier_label:
            return None

        expected_limit = _expected_limit(mean, multiplier)
        if expected_limit != doc.get("credit_limit_idr"):
            return None

        as_of_date = doc.get("as_of_date")
        if not isinstance(as_of_date, str) or not as_of_date:
            return None

        reason_codes = doc.get("reason_codes")
        if _valid_reason_codes(reason_codes):
            explanation_status = "available"
            reason_codes_out = reason_codes
        else:
            explanation_status = "unavailable"
            reason_codes_out = []

        return {
            "score": score,
            "average_balance_36m": mean,
            "credit_limit_idr": doc["credit_limit_idr"],
            "as_of_date": as_of_date,
            "model_version": doc["model_version"],
            "tier": tier_label,
            "reason_codes": reason_codes_out,
            "explanation_status": explanation_status,
        }
