from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


NUMERIC_FEATURES = [
    "complaint_count",
    "crash_count",
    "fire_count",
    "injury_count",
    "death_count",
    "severe_complaint_count",
    "rolling_4w_complaint_mean_prior",
    "rolling_8w_complaint_mean_prior",
    "rolling_8w_complaint_std_prior",
    "complaint_spike_z",
    "baseline_risk_score",
]

PREDICTION_COLUMNS = [
    "split",
    "make",
    "model",
    "model_year",
    "component_family",
    "week_start",
    "as_of_date",
    "next_90d_recall",
    "recall_count_90d",
    "days_to_first_recall",
    "matched_campaign_numbers",
    "rule_score",
    "logistic_score",
    "complaint_count",
    "severe_complaint_count",
    "complaint_spike_z",
    "baseline_risk_score",
]

COEFFICIENT_COLUMNS = ["feature", "coefficient"]


@dataclass
class Standardizer:
    means: list[float]
    stds: list[float]

    def transform_one(self, values: list[float]) -> list[float]:
        return [
            (value - mean) / std if std > 0 else 0.0
            for value, mean, std in zip(values, self.means, self.stds, strict=True)
        ]


@dataclass
class LogisticModel:
    weights: list[float]
    intercept: float
    standardizer: Standardizer
    features: list[str]

    def predict_proba_one(self, row: dict[str, Any]) -> float:
        x = self.standardizer.transform_one([parse_float(row.get(name)) for name in self.features])
        logit = self.intercept + sum(weight * value for weight, value in zip(self.weights, x, strict=True))
        return sigmoid(logit)


def parse_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_int(value: Any) -> int:
    return int(parse_float(value))


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def labeled_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if str(row.get("label_available")) == "1" and str(row.get("next_90d_recall")) in {"0", "1"}
    ]


def temporal_train_test_split(
    rows: list[dict[str, str]],
    test_fraction: float = 0.25,
    min_test_positives: int = 3,
) -> tuple[list[dict[str, str]], list[dict[str, str]], str]:
    """Chronological split with a small adjustment for rare positives.

    We start with the last `test_fraction` rows as test, then move the cutoff
    earlier if the test split has too few positives. This keeps the evaluation
    mostly time-based while avoiding a useless all-negative test set.
    """

    sorted_rows = sorted(rows, key=lambda row: (row["as_of_date"], row["make"], row["model"]))
    if len(sorted_rows) < 2:
        return sorted_rows, [], ""

    total_pos = sum(parse_int(row["next_90d_recall"]) for row in sorted_rows)
    desired_test_pos = min(max(1, min_test_positives), max(1, total_pos // 3))

    cutoff_index = max(1, int(len(sorted_rows) * (1 - test_fraction)))

    def split_at(index: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        return sorted_rows[:index], sorted_rows[index:]

    train_rows, test_rows = split_at(cutoff_index)

    while cutoff_index > 1:
        train_pos = sum(parse_int(row["next_90d_recall"]) for row in train_rows)
        test_pos = sum(parse_int(row["next_90d_recall"]) for row in test_rows)
        if train_pos > 0 and test_pos >= desired_test_pos:
            break
        cutoff_index -= max(1, len(sorted_rows) // 100)
        train_rows, test_rows = split_at(cutoff_index)

    cutoff_date = train_rows[-1]["as_of_date"] if train_rows else ""
    return train_rows, test_rows, cutoff_date


def fit_standardizer(rows: list[dict[str, Any]], features: list[str]) -> Standardizer:
    matrix = [[parse_float(row.get(name)) for name in features] for row in rows]
    if not matrix:
        return Standardizer([0.0] * len(features), [1.0] * len(features))

    means = []
    stds = []
    for col_idx in range(len(features)):
        values = [row[col_idx] for row in matrix]
        avg = sum(values) / len(values)
        if len(values) < 2:
            std = 1.0
        else:
            variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
            std = math.sqrt(variance) or 1.0
        means.append(avg)
        stds.append(std)
    return Standardizer(means, stds)


def train_logistic_regression(
    rows: list[dict[str, Any]],
    features: list[str] | None = None,
    epochs: int = 800,
    learning_rate: float = 0.05,
    l2: float = 0.01,
) -> LogisticModel:
    features = features or NUMERIC_FEATURES
    standardizer = fit_standardizer(rows, features)
    x_matrix = [
        standardizer.transform_one([parse_float(row.get(name)) for name in features])
        for row in rows
    ]
    y = [parse_int(row["next_90d_recall"]) for row in rows]

    pos_count = sum(y)
    neg_count = len(y) - pos_count
    if pos_count == 0 or neg_count == 0:
        # Degenerate fallback. The intercept is the empirical log-odds with smoothing.
        p = (pos_count + 1) / (len(y) + 2)
        return LogisticModel([0.0] * len(features), math.log(p / (1 - p)), standardizer, features)

    # Cap class weights to avoid unstable updates in tiny rare-event samples.
    pos_weight = min(50.0, len(y) / (2 * pos_count))
    neg_weight = min(50.0, len(y) / (2 * neg_count))

    weights = [0.0] * len(features)
    intercept = math.log((pos_count + 1) / (neg_count + 1))

    for _ in range(epochs):
        grad_weights = [0.0] * len(features)
        grad_intercept = 0.0
        total_weight = 0.0

        for x, target in zip(x_matrix, y, strict=True):
            pred = sigmoid(intercept + sum(w * v for w, v in zip(weights, x, strict=True)))
            sample_weight = pos_weight if target == 1 else neg_weight
            error = sample_weight * (pred - target)
            total_weight += sample_weight
            grad_intercept += error
            for idx, value in enumerate(x):
                grad_weights[idx] += error * value

        denom = total_weight or len(y)
        intercept -= learning_rate * (grad_intercept / denom)
        for idx in range(len(weights)):
            grad = (grad_weights[idx] / denom) + l2 * weights[idx]
            weights[idx] -= learning_rate * grad

    return LogisticModel(weights, intercept, standardizer, features)


def score_rows(
    rows: list[dict[str, Any]],
    model: LogisticModel,
    split_name: str,
) -> list[dict[str, Any]]:
    scored = []
    for row in rows:
        output = dict(row)
        output["split"] = split_name
        output["rule_score"] = parse_float(row.get("baseline_risk_score"))
        output["logistic_score"] = round(model.predict_proba_one(row), 8)
        scored.append(output)
    return scored


def average_precision(y_true: list[int], y_score: list[float]) -> float:
    positives = sum(y_true)
    if positives == 0:
        return 0.0

    paired = sorted(zip(y_score, y_true, strict=True), key=lambda item: item[0], reverse=True)
    hit_count = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(paired, start=1):
        if label == 1:
            hit_count += 1
            precision_sum += hit_count / rank
    return precision_sum / positives


def brier_score(y_true: list[int], y_score: list[float]) -> float:
    if not y_true:
        return 0.0
    return sum((score - target) ** 2 for target, score in zip(y_true, y_score, strict=True)) / len(y_true)


def precision_recall_at_k(y_true: list[int], y_score: list[float], k: int) -> dict[str, float]:
    if not y_true:
        return {"k": k, "precision": 0.0, "recall": 0.0, "hits": 0}
    paired = sorted(zip(y_score, y_true, strict=True), key=lambda item: item[0], reverse=True)
    top = paired[: min(k, len(paired))]
    hits = sum(label for _, label in top)
    positives = sum(y_true)
    return {
        "k": k,
        "precision": round(hits / len(top), 6) if top else 0.0,
        "recall": round(hits / positives, 6) if positives else 0.0,
        "hits": hits,
    }


def evaluate_scores(
    rows: list[dict[str, Any]],
    score_column: str,
    ks: list[int] | None = None,
) -> dict[str, Any]:
    ks = ks or [5, 10, 25, 50, 100]
    y_true = [parse_int(row["next_90d_recall"]) for row in rows]
    y_score = [parse_float(row.get(score_column)) for row in rows]
    positives = sum(y_true)

    return {
        "row_count": len(rows),
        "positive_count": positives,
        "positive_rate": round(positives / len(rows), 6) if rows else 0.0,
        "average_precision": round(average_precision(y_true, y_score), 6),
        "brier_score": round(brier_score(y_true, y_score), 6),
        "precision_recall_at_k": [precision_recall_at_k(y_true, y_score, k) for k in ks],
    }


def coefficient_rows(model: LogisticModel) -> list[dict[str, Any]]:
    rows = [{"feature": "__intercept__", "coefficient": round(model.intercept, 8)}]
    rows.extend(
        {"feature": feature, "coefficient": round(weight, 8)}
        for feature, weight in zip(model.features, model.weights, strict=True)
    )
    return rows

