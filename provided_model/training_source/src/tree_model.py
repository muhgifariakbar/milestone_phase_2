"""Portable numeric CART classifier with disjoint sigmoid calibration."""

import math
from dataclasses import dataclass


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def logit(probability: float) -> float:
    p = min(0.999999, max(0.000001, probability))
    return math.log(p / (1 - p))


def gini(positives: int, count: int) -> float:
    if count == 0:
        return 0.0
    p = positives / count
    return 2 * p * (1 - p)


@dataclass
class TreeModel:
    features: tuple[str, ...]
    root: dict
    calibration_slope: float = 1.0
    calibration_intercept: float = 0.0

    @classmethod
    def fit(cls, rows: list[dict], labels: list[int], features: tuple[str, ...],
            max_depth: int = 5, min_leaf: int = 60) -> "TreeModel":
        if len(rows) != len(labels) or not rows:
            raise ValueError("nonempty, aligned training rows and labels required")
        if any(label not in (0, 1) for label in labels):
            raise ValueError("labels must be binary")

        def build(indices: list[int], depth: int) -> dict:
            positive = sum(labels[index] for index in indices)
            node = {"count": len(indices), "positive": positive,
                    "risk": positive / len(indices)}
            if depth >= max_depth or len(indices) < 2 * min_leaf or positive in (0, len(indices)):
                return node
            parent_impurity = gini(positive, len(indices))
            best: tuple[float, str, float, list[int], list[int]] | None = None
            for feature in features:
                values = sorted({float(rows[index][feature]) for index in indices})
                if len(values) < 2:
                    continue
                positions = sorted({int(i * (len(values) - 1) / 33) for i in range(1, 33)})
                thresholds = [(values[pos] + values[pos + 1]) / 2 for pos in positions
                              if pos + 1 < len(values)]
                for threshold in thresholds:
                    left = [index for index in indices if float(rows[index][feature]) <= threshold]
                    if not min_leaf <= len(left) <= len(indices) - min_leaf:
                        continue
                    left_set = set(left)
                    right = [index for index in indices if index not in left_set]
                    left_pos = sum(labels[index] for index in left)
                    right_pos = positive - left_pos
                    impurity = (len(left) * gini(left_pos, len(left))
                                + len(right) * gini(right_pos, len(right))) / len(indices)
                    gain = parent_impurity - impurity
                    if best is None or gain > best[0] + 1e-12:
                        best = (gain, feature, threshold, left, right)
            if best is None or best[0] <= 1e-12:
                return node
            _, feature, threshold, left, right = best
            node.update({"feature": feature, "threshold": threshold,
                         "left": build(left, depth + 1), "right": build(right, depth + 1)})
            return node

        return cls(features=features, root=build(list(range(len(rows))), 0))

    def path(self, row: dict) -> list[tuple[dict, dict, str]]:
        node = self.root
        result = []
        while "feature" in node:
            side = "left" if float(row[node["feature"]]) <= node["threshold"] else "right"
            child = node[side]
            result.append((node, child, side))
            node = child
        return result

    def raw_probability(self, row: dict) -> float:
        path = self.path(row)
        return float(path[-1][1]["risk"] if path else self.root["risk"])

    def probability(self, row: dict) -> float:
        return sigmoid(self.calibration_slope * logit(self.raw_probability(row))
                       + self.calibration_intercept)

    def calibrate(self, rows: list[dict], labels: list[int]) -> None:
        if len(rows) != len(labels) or not rows:
            raise ValueError("calibration rows and labels required")
        x = [logit(self.raw_probability(row)) for row in rows]
        slope, intercept = 1.0, 0.0
        for _ in range(2500):
            residual = [sigmoid(slope * value + intercept) - label
                        for value, label in zip(x, labels)]
            gradient_slope = sum(error * value for error, value in zip(residual, x)) / len(x)
            gradient_intercept = sum(residual) / len(x)
            slope = max(0.001, slope - 0.02 * gradient_slope)
            intercept -= 0.02 * gradient_intercept
        self.calibration_slope = slope
        self.calibration_intercept = intercept

    def to_dict(self) -> dict:
        return {"algorithm": "numeric_cart_gini_v1", "features": list(self.features),
                "max_depth": 5, "min_leaf": 60, "root": self.root,
                "calibration": {"method": "sigmoid", "slope": self.calibration_slope,
                                "intercept": self.calibration_intercept}}

    @classmethod
    def from_dict(cls, payload: dict) -> "TreeModel":
        if payload.get("algorithm") != "numeric_cart_gini_v1":
            raise ValueError("unsupported model algorithm")
        return cls(tuple(payload["features"]), payload["root"],
                   float(payload["calibration"]["slope"]),
                   float(payload["calibration"]["intercept"]))


def roc_auc(labels: list[int], predictions: list[float]) -> float:
    pairs = sorted(zip(predictions, labels))
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        raise ValueError("AUC requires both classes")
    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        end = index + 1
        while end < len(pairs) and pairs[end][0] == pairs[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2
        rank_sum += average_rank * sum(label for _, label in pairs[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def brier(labels: list[int], predictions: list[float]) -> float:
    return sum((label - prediction) ** 2 for label, prediction in zip(labels, predictions)) / len(labels)
