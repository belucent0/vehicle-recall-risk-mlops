from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINES_DIR = PROJECT_ROOT / "pipelines"
if str(PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINES_DIR))

from pipelines.evaluate_model_gate import evaluate_promotion  # noqa: E402


def base_summary(model_artifact: Path, predictions_csv: Path) -> dict[str, object]:
    return {
        "model_artifact": str(model_artifact),
        "predictions_csv": str(predictions_csv),
        "split": {
            "test": {
                "row_count": 100,
                "positive_count": 20,
            }
        },
        "test_metrics": {
            "rule": {
                "average_precision": 0.10,
                "brier_score": 0.20,
                "precision_recall_at_k": [
                    {"k": 25, "precision": 0.08, "recall": 0.10, "hits": 2},
                ],
            },
            "logistic": {
                "average_precision": 0.12,
                "brier_score": 0.18,
                "precision_recall_at_k": [
                    {"k": 25, "precision": 0.00, "recall": 0.00, "hits": 0},
                ],
            },
        },
    }


def test_evaluate_promotion_approves_with_non_blocking_top_k_warning(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_1"
    run_dir.mkdir()
    model_artifact = tmp_path / "model.joblib"
    predictions_csv = tmp_path / "predictions.csv"
    model_artifact.write_text("model", encoding="utf-8")
    predictions_csv.write_text("predictions", encoding="utf-8")

    decision = evaluate_promotion(
        summary=base_summary(model_artifact, predictions_csv),
        processed_run_dir=run_dir,
        min_test_positives=10,
        min_ap_delta=0.0,
        max_brier_regression=0.0,
        precision_k=25,
        require_precision_at_k=False,
    )

    assert decision["promotion_status"] == "approved"
    assert decision["approved"] is True
    assert len(decision["warnings"]) == 1
    assert decision["warnings"][0]["name"] == "logistic_precision_at_25_not_worse_than_rule"


def test_evaluate_promotion_rejects_when_ap_is_worse(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_1"
    run_dir.mkdir()
    model_artifact = tmp_path / "model.joblib"
    predictions_csv = tmp_path / "predictions.csv"
    model_artifact.write_text("model", encoding="utf-8")
    predictions_csv.write_text("predictions", encoding="utf-8")

    summary = base_summary(model_artifact, predictions_csv)
    summary["test_metrics"]["logistic"]["average_precision"] = 0.05  # type: ignore[index]

    decision = evaluate_promotion(
        summary=summary,
        processed_run_dir=run_dir,
        min_test_positives=10,
        min_ap_delta=0.0,
        max_brier_regression=0.0,
        precision_k=25,
        require_precision_at_k=False,
    )

    assert decision["promotion_status"] == "rejected"
    assert decision["approved"] is False
    assert any(
        check["name"] == "logistic_ap_not_worse_than_rule"
        for check in decision["blocking_failures"]
    )
