"""Published classroom score and limit policy. No real lending use."""

from decimal import Decimal, ROUND_DOWN


FEATURES = (
    "average_balance_36m",
    "balance_volatility",
    "on_time_payment_rate",
    "late_payment_count_36m",
    "overdraft_count_36m",
    "inflow_stability",
)

LABELS = {
    "average_balance_36m": "average account balance",
    "balance_volatility": "changes in monthly balance",
    "on_time_payment_rate": "on-time payment record",
    "late_payment_count_36m": "late payments",
    "overdraft_count_36m": "overdrafts",
    "inflow_stability": "regularity of account inflows",
}


def risk_to_score(probability: float) -> int:
    if not 0 <= probability <= 1:
        raise ValueError("risk probability must be between zero and one")
    return max(300, min(850, round(850 - 550 * probability)))


def score_tier(score: int) -> tuple[str, Decimal]:
    if not 300 <= score <= 850:
        raise ValueError("score outside classroom range")
    if score < 550:
        return "higher risk", Decimal("0.5")
    if score < 650:
        return "moderate risk", Decimal("1.0")
    if score < 750:
        return "lower risk", Decimal("1.5")
    return "lowest risk", Decimal("2.0")


def credit_limit(average_balance: float, score: int) -> int:
    if average_balance < 0:
        raise ValueError("average balance cannot be negative")
    _, multiple = score_tier(score)
    raw = min(Decimal(str(average_balance)) * multiple, Decimal("100000000"))
    return int((raw / Decimal("100000")).to_integral_value(rounding=ROUND_DOWN) * 100000)
