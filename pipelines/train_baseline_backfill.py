from __future__ import annotations

import argparse
import json
import random
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
    save_model_artifact,
    score_rows,
    temporal_train_test_split,
    train_logistic_regression,
    write_csv_rows,
)


PROCESSED_BACKFILL_DIR = PROJECT_ROOT / "data" / "processed" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def latest_run_dir() -> Path:
    candidates = [path for path in PROCESSED_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed backfill run directory under {PROCESSED_BACKFILL_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def split_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positives = sum(int(row["next_90d_recall"]) for row in rows)
    return {
        "row_count": len(rows),
        "positive_count": positives,
        "positive_rate": round(positives / len(rows), 6) if rows else 0.0,
        "min_as_of_date": min((row["as_of_date"] for row in rows), default=""),
        "max_as_of_date": max((row["as_of_date"] for row in rows), default=""),
    }


def sample_training_rows(
    train_rows: list[dict[str, Any]],
    negative_ratio: int = 20,
    max_rows: int = 100_000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    positives = [row for row in train_rows if str(row["next_90d_recall"]) == "1"]
    negatives = [row for row in train_rows if str(row["next_90d_recall"]) == "0"]

    max_negative_by_ratio = len(positives) * negative_ratio
    max_negative_by_total = max(0, max_rows - len(positives))
    negative_count = min(len(negatives), max_negative_by_ratio, max_negative_by_total)

    rng = random.Random(seed)
    sampled_negatives = rng.sample(negatives, negative_count) if negative_count < len(negatives) else negatives
    sampled = positives + sampled_negatives
    sampled.sort(key=lambda row: (row["as_of_date"], row["make"], row["model"], row["component_family"]))
    return sampled


def top_predictions(rows: list[dict[str, Any]], score_column: str, limit: int = 20) -> list[dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: float(row.get(score_column) or 0.0), reverse=True)
    output = []
    for idx, row in enumerate(sorted_rows[:limit], start=1):
        output.append(
            {
                "rank": idx,
                "make": row.get("make"),
                "model": row.get("model"),
                "model_year": row.get("model_year"),
                "component_family": row.get("component_family"),
                "as_of_date": row.get("as_of_date"),
                "label": row.get("next_90d_recall"),
                "days_to_first_recall": row.get("days_to_first_recall"),
                "score": row.get(score_column),
                "matched_campaign_numbers": row.get("matched_campaign_numbers"),
            }
        )
    return output


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
        "# Backfill Baseline Model Results",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Split cutoff as-of date: `{summary['split']['cutoff_as_of_date']}`",
        f"- Model type: `{summary['model_type']}`",
        f"- Logistic train sample rows: `{summary['logistic_training_sample']['row_count']}`",
        f"- Model artifact: `{summary['model_artifact']}`",
        "",
        "## Split",
        "",
        "| Split | Rows | Positives | Positive rate | Date range |",
        "|---|---:|---:|---:|---|",
    ]

    for split_name in ["train", "test"]:
        item = summary["split"][split_name]
        lines.append(
            f"| {split_name} | {item['row_count']} | {item['positive_count']} "
            f"| {item['positive_rate']} | {item['min_as_of_date']} ~ {item['max_as_of_date']} |"
        )

    lines.extend(["", "## Test Metrics", ""])
    lines.extend(metric_lines("Rule baseline: baseline_risk_score", summary["test_metrics"]["rule"]))
    lines.extend(
        metric_lines(
            "Logistic baseline: scikit-learn Pipeline + StandardScaler + class_weight=balanced",
            summary["test_metrics"]["logistic"],
        )
    )

    lines.extend(
        [
            "## Top Logistic Predictions on Test",
            "",
            "| Rank | Make | Model | Year | Component | As-of | Label | Days to Recall | Score | Campaigns |",
            "|---:|---|---|---:|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary["top_logistic_predictions"]:
        lines.append(
            f"| {row['rank']} | {row['make']} | {row['model']} | {row['model_year']} "
            f"| {row['component_family']} | {row['as_of_date']} | {row['label']} "
            f"| {row['days_to_first_recall']} | {row['score']} | {row['matched_campaign_numbers']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Smoke test보다 훨씬 큰 test set에서 baseline을 평가했다.",
            "- 이 문제는 positive rate가 매우 낮으므로 accuracy가 아니라 ranking metric을 본다.",
            "- Logistic baseline은 scikit-learn Pipeline(SimpleImputer, StandardScaler, LogisticRegression)으로 학습했다.",
            "- 학습 데이터는 positive 전체 + negative downsampling sample을 사용했다.",
            "- LogisticRegression은 `class_weight='balanced'`를 사용했다.",
            "- 다음 단계에서는 최신 risk score 리포트를 만들고 MVP 결과물을 정리한다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train/evaluate baseline models on backfill dataset.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest processed backfill run.")
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--max-iter", type=int, default=1000)
    parser.add_argument("--negative-ratio", type=int, default=20)
    parser.add_argument("--max-train-rows", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_run_dir = PROCESSED_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    dataset_path = processed_run_dir / "training_dataset_labeled_only.csv"

    print("Reading labeled dataset...", flush=True)
    rows = labeled_rows(read_csv_rows(dataset_path))
    train_rows, test_rows, cutoff_date = temporal_train_test_split(rows)

    print("Sampling train rows for logistic baseline...", flush=True)
    logistic_train_rows = sample_training_rows(
        train_rows,
        negative_ratio=args.negative_ratio,
        max_rows=args.max_train_rows,
        seed=args.seed,
    )

    print(f"Training logistic baseline on {len(logistic_train_rows)} rows...", flush=True)
    model = train_logistic_regression(
        logistic_train_rows,
        epochs=args.epochs,
        max_iter=args.max_iter,
        random_state=args.seed,
    )

    print("Scoring test rows...", flush=True)
    test_predictions = score_rows(test_rows, model, "test")

    predictions_path = processed_run_dir / "baseline_test_predictions.csv"
    coefficients_path = processed_run_dir / "baseline_logistic_coefficients.csv"
    model_artifact_path = processed_run_dir / "sklearn_logistic_pipeline.joblib"
    write_csv_rows(predictions_path, test_predictions, PREDICTION_COLUMNS)
    write_csv_rows(coefficients_path, coefficient_rows(model), COEFFICIENT_COLUMNS)
    save_model_artifact(model, model_artifact_path)

    logistic_sample_summary = split_summary(logistic_train_rows)
    summary = {
        "source_run_id": run_id,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "input_dataset": display_path(dataset_path),
        "predictions_csv": display_path(predictions_path),
        "coefficients_csv": display_path(coefficients_path),
        "model_artifact": display_path(model_artifact_path),
        "model_type": model.model_type,
        "model_library": "scikit-learn",
        "model_config": {
            "pipeline": ["SimpleImputer", "StandardScaler", "LogisticRegression"],
            "class_weight": "balanced",
            "max_iter": max(args.max_iter, args.epochs, 1000),
            "negative_ratio": args.negative_ratio,
            "max_train_rows": args.max_train_rows,
            "seed": args.seed,
        },
        "split": {
            "cutoff_as_of_date": cutoff_date,
            "train": split_summary(train_rows),
            "test": split_summary(test_rows),
        },
        "logistic_training_sample": logistic_sample_summary,
        "test_metrics": {
            "rule": evaluate_scores(test_predictions, "rule_score"),
            "logistic": evaluate_scores(test_predictions, "logistic_score"),
        },
        "top_logistic_predictions": top_predictions(test_predictions, "logistic_score"),
    }

    summary_path = processed_run_dir / "baseline_model_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "backfill_baseline_model_latest.md"
    write_markdown_report(summary, report_path)

    docs_result_path = DOCS_DIR / "BACKFILL_BASELINE_MODEL_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Train rows:       {summary['split']['train']['row_count']}")
    print(f"Train positives:  {summary['split']['train']['positive_count']}")
    print(f"Test rows:        {summary['split']['test']['row_count']}")
    print(f"Test positives:   {summary['split']['test']['positive_count']}")
    print(f"Rule AP:          {summary['test_metrics']['rule']['average_precision']}")
    print(f"Logistic AP:      {summary['test_metrics']['logistic']['average_precision']}")
    print(f"Wrote:            {display_path(predictions_path)}")
    print(f"Wrote:            {display_path(model_artifact_path)}")
    print(f"Wrote:            {display_path(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
