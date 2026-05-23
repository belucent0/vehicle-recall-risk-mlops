from __future__ import annotations

from recall_risk.models.baseline import (
    NUMERIC_FEATURES,
    coefficient_rows,
    score_rows,
    train_logistic_regression,
)


def make_row(label: int, complaint_count: int, spike_score: float) -> dict[str, object]:
    row: dict[str, object] = {
        "next_90d_recall": label,
        "baseline_risk_score": spike_score,
    }
    for feature in NUMERIC_FEATURES:
        row[feature] = 0

    row["complaint_count"] = complaint_count
    row["severe_complaint_count"] = complaint_count
    row["complaint_spike_z"] = spike_score
    row["baseline_risk_score"] = spike_score
    return row


def test_train_logistic_regression_uses_sklearn_pipeline() -> None:
    rows = [
        make_row(0, 0, 0.0),
        make_row(0, 1, 0.1),
        make_row(0, 1, 0.2),
        make_row(1, 8, 2.5),
        make_row(1, 9, 3.0),
        make_row(1, 10, 3.5),
    ]

    model = train_logistic_regression(rows, max_iter=1000)
    scored = score_rows(rows, model, "test")
    coefficients = coefficient_rows(model)

    assert model.model_type == "sklearn_logistic_regression_pipeline"
    assert model.pipeline.named_steps["classifier"].class_weight == "balanced"
    assert all(0.0 <= row["logistic_score"] <= 1.0 for row in scored)
    assert any(row["feature"] == "__intercept__" for row in coefficients)

