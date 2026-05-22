from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recall_risk.models.baseline import (  # noqa: E402
    COEFFICIENT_COLUMNS,
    PREDICTION_COLUMNS,
    coefficient_rows,
    evaluate_scores,
    labeled_rows,
    read_csv_rows,
    score_rows,
    temporal_train_test_split,
    train_logistic_regression,
    write_csv_rows,
)


PROCESSED_SMOKE_DIR = PROJECT_ROOT / "data" / "processed" / "smoke_test"
REPORTS_DIR = PROJECT_ROOT / "reports"


def latest_processed_run_dir() -> Path:
    candidates = [path for path in PROCESSED_SMOKE_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed smoke test run directory under {PROCESSED_SMOKE_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train/evaluate baseline recall-risk models.")
    parser.add_argument("--run-id", help="Smoke test run id. Defaults to latest processed run.")
    parser.add_argument("--epochs", type=int, default=800)
    return parser.parse_args()


def metric_lines(title: str, metrics: dict[str, Any]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {metrics['row_count']} |",
        f"| Positives | {metrics['positive_count']} |",
        f"| Positive rate | {metrics['positive_rate']} |",
        f"| Average precision | {metrics['average_precision']} |",
        f"| Brier score | {metrics['brier_score']} |",
        "",
        "| K | Precision@K | Recall@K | Hits |",
        "|---:|---:|---:|---:|",
    ]
    for item in metrics["precision_recall_at_k"]:
        lines.append(f"| {item['k']} | {item['precision']} | {item['recall']} | {item['hits']} |")
    lines.append("")
    return lines


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# Baseline Model Sample Report",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Split cutoff as-of date: `{summary['split']['cutoff_as_of_date']}`",
        "",
        "## Split",
        "",
        "| Split | Rows | Positives | Positive rate |",
        "|---|---:|---:|---:|",
    ]

    for split_name in ["train", "test"]:
        item = summary["split"][split_name]
        lines.append(
            f"| {split_name} | {item['row_count']} | {item['positive_count']} "
            f"| {item['positive_rate']} |"
        )

    lines.extend(["", "## Test Metrics", ""])
    lines.extend(metric_lines("Rule baseline: baseline_risk_score", summary["test_metrics"]["rule"]))
    lines.extend(metric_lines("Logistic baseline", summary["test_metrics"]["logistic"]))

    lines.extend(
        [
            "## Notes",
            "",
            "- This is still a smoke-test-scale dataset.",
            "- The rule baseline uses `baseline_risk_score` directly.",
            "- The logistic baseline is a pure-Python weighted logistic regression using numeric features only.",
            "- Accuracy is intentionally omitted because the task is a rare-event ranking problem.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def split_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = sum(int(row["next_90d_recall"]) for row in rows)
    return {
        "row_count": len(rows),
        "positive_count": positives,
        "positive_rate": round(positives / len(rows), 6) if rows else 0.0,
        "min_as_of_date": min((row["as_of_date"] for row in rows), default=""),
        "max_as_of_date": max((row["as_of_date"] for row in rows), default=""),
    }


def main() -> int:
    args = parse_args()
    processed_run_dir = (
        PROCESSED_SMOKE_DIR / args.run_id if args.run_id else latest_processed_run_dir()
    )
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    dataset_path = processed_run_dir / "training_dataset_labeled_only.csv"
    rows = labeled_rows(read_csv_rows(dataset_path))
    train_rows, test_rows, cutoff_date = temporal_train_test_split(rows)

    model = train_logistic_regression(train_rows, epochs=args.epochs)
    train_predictions = score_rows(train_rows, model, "train")
    test_predictions = score_rows(test_rows, model, "test")
    all_predictions = train_predictions + test_predictions

    predictions_path = processed_run_dir / "baseline_predictions.csv"
    coefficients_path = processed_run_dir / "baseline_logistic_coefficients.csv"

    write_csv_rows(predictions_path, all_predictions, PREDICTION_COLUMNS)
    write_csv_rows(coefficients_path, coefficient_rows(model), COEFFICIENT_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "input_dataset": str(dataset_path.relative_to(PROJECT_ROOT)),
        "predictions_csv": str(predictions_path.relative_to(PROJECT_ROOT)),
        "coefficients_csv": str(coefficients_path.relative_to(PROJECT_ROOT)),
        "split": {
            "cutoff_as_of_date": cutoff_date,
            "train": split_summary(train_rows),
            "test": split_summary(test_rows),
        },
        "test_metrics": {
            "rule": evaluate_scores(test_predictions, "rule_score"),
            "logistic": evaluate_scores(test_predictions, "logistic_score"),
        },
    }

    summary_path = processed_run_dir / "baseline_model_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "baseline_model_latest.md"
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_markdown_report(summary, report_path)

    print(f"Train rows:       {summary['split']['train']['row_count']}")
    print(f"Train positives:  {summary['split']['train']['positive_count']}")
    print(f"Test rows:        {summary['split']['test']['row_count']}")
    print(f"Test positives:   {summary['split']['test']['positive_count']}")
    print(f"Rule AP:          {summary['test_metrics']['rule']['average_precision']}")
    print(f"Logistic AP:      {summary['test_metrics']['logistic']['average_precision']}")
    print(f"Wrote:            {predictions_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:            {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

