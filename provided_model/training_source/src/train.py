"""Organizer-only training, evaluation, and assessment materialization."""

import argparse
import json
import random
from pathlib import Path

from .data import connect
from .policy import FEATURES, LABELS, credit_limit, risk_to_score, score_tier
from .tree_model import TreeModel, brier, roc_auc


MODEL_VERSION = "synthetic-cart-v2"


def split_indices(labels: list[int], seed: int = 42) -> tuple[list[int], list[int], list[int]]:
    rng = random.Random(seed)
    groups = {0: [], 1: []}
    for index, label in enumerate(labels):
        groups[label].append(index)
    train, calibration, test = [], [], []
    for indices in groups.values():
        rng.shuffle(indices)
        first = int(0.6 * len(indices))
        second = int(0.8 * len(indices))
        train.extend(indices[:first])
        calibration.extend(indices[first:second])
        test.extend(indices[second:])
    for group in (train, calibration, test):
        group.sort()
    return train, calibration, test


def local_reasons(model: TreeModel, row: dict) -> list[dict]:
    adverse, favorable = [], []
    for parent, child, side in model.path(row):
        change = child["risk"] - parent["risk"]
        if abs(change) < 1e-12:
            continue
        feature = parent["feature"]
        direction = "higher risk" if change > 0 else "lower risk"
        comparator = "at or below" if side == "left" else "above"
        description = (
            f"{LABELS[feature]} ({float(row[feature]):,.2f}) was {comparator} "
            f"the model threshold ({parent['threshold']:,.2f}), "
            f"{'raising' if change > 0 else 'lowering'} modeled risk on this path"
        )
        item = {"feature": feature, "direction": direction,
                "observed_value": float(row[feature]), "threshold": parent["threshold"],
                "description": description, "path_risk_change": round(change, 6)}
        (adverse if change > 0 else favorable).append((abs(change), item))
    chosen = sorted(adverse, key=lambda item: item[0], reverse=True)[:3]
    if not chosen:
        chosen = sorted(favorable, key=lambda item: item[0], reverse=True)[:2]
    return [item for _, item in chosen]


def train(db_path: Path, model_path: Path, report_path: Path) -> dict:
    with connect(db_path) as db:
        records = [dict(row) for row in db.execute("SELECT * FROM features ORDER BY customer_id")]
    if len(records) < 100:
        raise ValueError("at least 100 training records required")
    labels = [int(row["missed_payment_next_12m"]) for row in records]
    train_idx, calibration_idx, test_idx = split_indices(labels)
    model = TreeModel.fit([records[i] for i in train_idx], [labels[i] for i in train_idx], FEATURES)
    model.calibrate([records[i] for i in calibration_idx],
                    [labels[i] for i in calibration_idx])
    test_labels = [labels[i] for i in test_idx]
    predictions = [model.probability(records[i]) for i in test_idx]
    baseline = sum(labels[i] for i in train_idx) / len(train_idx)
    report = {
        "model_version": MODEL_VERSION, "seed": 20260927,
        "feature_names": list(FEATURES), "label": "missed_payment_next_12m",
        "split_counts": {"train": len(train_idx), "calibration": len(calibration_idx),
                         "test": len(test_idx)},
        "test_event_rate": round(sum(test_labels) / len(test_labels), 4),
        "roc_auc": round(roc_auc(test_labels, predictions), 4),
        "brier_score": round(brier(test_labels, predictions), 4),
        "baseline_brier_score": round(brier(test_labels, [baseline] * len(test_idx)), 4),
        "limitations": ["All histories and labels are fictional.",
                        "Held-out performance does not establish real lending validity or fairness."],
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {"model_version": MODEL_VERSION, **model.to_dict()}
    model_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with connect(db_path) as db:
        db.execute("DELETE FROM assessments")
        for row in records:
            customer_id = row["customer_id"]
            monthly = db.execute(
                "SELECT COUNT(*) AS n, AVG(closing_balance_idr) AS avg_balance "
                "FROM monthly_balances WHERE customer_id=?", (customer_id,)
            ).fetchone()
            if monthly["n"] != 36:
                continue
            risk = model.probability(row)
            score = risk_to_score(risk)
            tier, _ = score_tier(score)
            db.execute("INSERT INTO assessments VALUES (?,?,?,?,?,?,?,?)", (
                customer_id, row["as_of_date"], MODEL_VERSION, risk, score, tier,
                credit_limit(float(monthly["avg_balance"]), score),
                json.dumps(local_reasons(model, row)),
            ))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("artifacts/bank.db"))
    parser.add_argument("--model", type=Path, default=Path("artifacts/model.json"))
    parser.add_argument("--report", type=Path, default=Path("artifacts/evaluation.json"))
    args = parser.parse_args()
    print(json.dumps(train(args.db, args.model, args.report), indent=2))


if __name__ == "__main__":
    main()
