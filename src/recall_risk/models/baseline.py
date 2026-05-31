from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


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

LOGISTIC_MODEL_VERSION = "sklearn_logistic_v1"

PREDICTION_COLUMNS = [
    "source_run_id",
    "model_version",
    "model_type",
    "model_library",
    "scored_at_utc",
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

COEFFICIENT_COLUMNS = [
    "source_run_id",
    "model_version",
    "model_type",
    "model_library",
    "scored_at_utc",
    "feature",
    "coefficient",
]


@dataclass
class LogisticModel:
    pipeline: Pipeline
    features: list[str]
    model_type: str = "sklearn_logistic_regression_pipeline"

    def feature_frame(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        return rows_to_feature_frame(rows, self.features)

    def predict_proba_rows(self, rows: list[dict[str, Any]]) -> list[float]:
        if not rows:
            return []

        probabilities = self.pipeline.predict_proba(self.feature_frame(rows))
        classifier = self.pipeline.named_steps["classifier"]
        classes = list(getattr(classifier, "classes_", []))

        if 1 in classes:
            positive_index = classes.index(1)
            return [float(value) for value in probabilities[:, positive_index]]
        if classes == [1]:
            return [1.0] * len(rows)
        return [0.0] * len(rows)

    def predict_proba_one(self, row: dict[str, Any]) -> float:
        return self.predict_proba_rows([row])[0]


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


def rows_to_feature_frame(rows: list[dict[str, Any]], features: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [{name: parse_float(row.get(name)) for name in features} for row in rows],
        columns=features,
    )


def train_logistic_regression(
    rows: list[dict[str, Any]],
    features: list[str] | None = None,
    epochs: int = 800,
    l2: float = 0.01,
    learning_rate: float = 0.05,
    max_iter: int | None = None,
    random_state: int = 42,
) -> LogisticModel:
    """Fit a scikit-learn logistic baseline.

    `epochs` and `learning_rate` remain in the signature for backward compatibility
    with the earlier pure-Python baseline CLI. The current implementation uses
    scikit-learn's `LogisticRegression`; `epochs` is treated as a lower bound for
    `max_iter`.
    """

    features = features or NUMERIC_FEATURES
    y = [parse_int(row["next_90d_recall"]) for row in rows]

    if not y:
        classifier = DummyClassifier(strategy="constant", constant=0)
        x = rows_to_feature_frame([{}], features)
        classifier.fit(x, [0])
        pipeline = Pipeline([("classifier", classifier)])
        return LogisticModel(pipeline=pipeline, features=features, model_type="sklearn_dummy_classifier")

    x = rows_to_feature_frame(rows, features)
    effective_max_iter = max(max_iter or 0, epochs, 1000)

    if len(set(y)) < 2:
        classifier = DummyClassifier(strategy="constant", constant=y[0])
        pipeline = Pipeline([("classifier", classifier)])
    else:
        c_value = 1.0 / l2 if l2 > 0 else 1.0
        classifier = LogisticRegression(
            class_weight="balanced",
            C=c_value,
            max_iter=effective_max_iter,
            solver="lbfgs",
            random_state=random_state,
        )
        pipeline = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
                ("scaler", StandardScaler()),
                ("classifier", classifier),
            ]
        )

    pipeline.fit(x, y)
    return LogisticModel(pipeline=pipeline, features=features)


def score_rows(
    rows: list[dict[str, Any]],
    model: LogisticModel,
    split_name: str,
    *,
    source_run_id: str = "",
    model_version: str = LOGISTIC_MODEL_VERSION,
    scored_at_utc: str = "",
    model_library: str = "scikit-learn",
) -> list[dict[str, Any]]:
    scored = []
    logistic_scores = model.predict_proba_rows(rows)
    for row, logistic_score in zip(rows, logistic_scores, strict=True):
        output = dict(row)
        output["source_run_id"] = source_run_id
        output["model_version"] = model_version
        output["model_type"] = model.model_type
        output["model_library"] = model_library
        output["scored_at_utc"] = scored_at_utc
        output["split"] = split_name
        output["rule_score"] = parse_float(row.get("baseline_risk_score"))
        output["logistic_score"] = round(logistic_score, 8)
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


def coefficient_rows(
    model: LogisticModel,
    *,
    source_run_id: str = "",
    model_version: str = LOGISTIC_MODEL_VERSION,
    scored_at_utc: str = "",
    model_library: str = "scikit-learn",
) -> list[dict[str, Any]]:
    classifier = model.pipeline.named_steps["classifier"]
    intercept = getattr(classifier, "intercept_", [0.0])
    coefficients = getattr(classifier, "coef_", [[0.0] * len(model.features)])

    def metadata_row(feature: str, coefficient: float) -> dict[str, Any]:
        return {
            "source_run_id": source_run_id,
            "model_version": model_version,
            "model_type": model.model_type,
            "model_library": model_library,
            "scored_at_utc": scored_at_utc,
            "feature": feature,
            "coefficient": round(coefficient, 8),
        }

    rows = [metadata_row("__intercept__", float(intercept[0]))]
    rows.extend(
        metadata_row(feature, float(weight))
        for feature, weight in zip(model.features, coefficients[0], strict=True)
    )
    return rows


def save_model_artifact(
    model: LogisticModel,
    path: Path,
    *,
    model_version: str = LOGISTIC_MODEL_VERSION,
) -> Path:
    import joblib

    payload = {
        "artifact_type": "sklearn_logistic_pipeline",
        "model_version": model_version,
        "model_type": model.model_type,
        "features": model.features,
        "pipeline": model.pipeline,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, path)
    return path
