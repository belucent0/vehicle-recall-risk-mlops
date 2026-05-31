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

from recall_risk.features.labels import (  # noqa: E402
    TRAINING_DATASET_COLUMNS,
    add_recall_labels,
    summarize_labeled_rows,
)
from recall_risk.features.weekly_features import (  # noqa: E402
    RISK_SCORE_COLUMNS,
    WEEKLY_FEATURE_COLUMNS,
    add_rolling_features,
    aggregate_weekly_complaints,
    latest_week_scores,
    read_csv_rows,
    write_csv_rows,
)


INTERIM_BACKFILL_DIR = PROJECT_ROOT / "data" / "interim" / "backfill"
PROCESSED_BACKFILL_DIR = PROJECT_ROOT / "data" / "processed" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def latest_run_dir() -> Path:
    candidates = [path for path in INTERIM_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No normalized backfill run directory under {INTERIM_BACKFILL_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def summarize_features(feature_rows: list[dict[str, Any]], risk_rows: list[dict[str, Any]]) -> dict[str, Any]:
    entity_keys = {
        (
            row["make"],
            row["model"],
            row["model_year"],
            row["component_primary"],
        )
        for row in feature_rows
    }
    weeks = sorted({row["week_start"] for row in feature_rows})
    nonzero_rows = [row for row in feature_rows if int(row["complaint_count"]) > 0]

    return {
        "feature_row_count": len(feature_rows),
        "entity_count": len(entity_keys),
        "week_count": len(weeks),
        "min_week": weeks[0] if weeks else "",
        "max_week": weeks[-1] if weeks else "",
        "nonzero_feature_row_count": len(nonzero_rows),
        "top_risk_rows": risk_rows[:15],
    }


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    features = summary["features"]
    labels = summary["labels"]

    lines = [
        "# Backfill Feature/Label Results",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Data as-of date: `{summary['data_as_of_date']}`",
        f"- Horizon days: `{summary['horizon_days']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Feature Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Feature rows | {features['feature_row_count']} |",
        f"| Entity count | {features['entity_count']} |",
        f"| Week count | {features['week_count']} |",
        f"| Week range | {features['min_week']} ~ {features['max_week']} |",
        f"| Non-zero complaint weeks | {features['nonzero_feature_row_count']} |",
        "",
        "## Label Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total rows | {labels['row_count']} |",
        f"| Label available rows | {labels['label_available_count']} |",
        f"| Label unavailable rows | {labels['label_unavailable_count']} |",
        f"| Positive rows | {labels['positive_count']} |",
        f"| Negative rows | {labels['negative_count']} |",
        f"| Positive rate | {labels['positive_rate']} |",
        f"| Positive entity count | {labels['positive_entity_count']} |",
        f"| Max as-of date | {labels['max_as_of_date']} |",
        f"| Max labeled as-of date | {labels['max_labeled_as_of_date']} |",
        "",
        "## Top Positive Components",
        "",
        "| Component family | Positive rows |",
        "|---|---:|",
    ]

    for name, count in labels["top_positive_components"]:
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "## Latest Week Top Risk Scores",
            "",
            "| Rank | Make | Model | Year | Component | Week | Complaints | Severe | Spike Z | Score |",
            "|---:|---|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in features["top_risk_rows"]:
        lines.append(
            f"| {row['rank']} | {row['make']} | {row['model']} | {row['model_year']} "
            f"| {row['component_primary']} | {row['week_start']} "
            f"| {row['complaint_count']} | {row['severe_complaint_count']} "
            f"| {row['complaint_spike_z']} | {row['baseline_risk_score']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- MVP backfill 데이터 기준 weekly features와 90일 recall labels를 생성했다.",
            "- `data_as_of_date=2026-05-15`를 사용해 미래 recall date가 label availability를 왜곡하지 않게 했다.",
            "- 다음 단계에서는 이 dataset으로 baseline model을 다시 평가한다.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build backfill weekly features and recall labels.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest normalized backfill run.")
    parser.add_argument("--horizon-days", type=int, default=90)
    parser.add_argument("--data-as-of-date", default="2026-05-15")
    parser.add_argument("--top-k", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    interim_run_dir = INTERIM_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not interim_run_dir.exists():
        raise FileNotFoundError(interim_run_dir)

    run_id = interim_run_dir.name
    output_dir = PROCESSED_BACKFILL_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    complaints_path = interim_run_dir / "complaints.csv"
    recalls_path = interim_run_dir / "recalls.csv"
    complaints = read_csv_rows(complaints_path)
    recalls = read_csv_rows(recalls_path)

    print("Aggregating weekly complaints...", flush=True)
    weekly_rows = aggregate_weekly_complaints(complaints)
    print(f"Weekly rows before rolling features: {len(weekly_rows)}", flush=True)

    print("Adding rolling features...", flush=True)
    feature_rows = add_rolling_features(weekly_rows)
    built_at_utc = datetime.now(UTC).isoformat()
    risk_rows = latest_week_scores(
        feature_rows,
        top_k=args.top_k,
        source_run_id=run_id,
        scored_at_utc=built_at_utc,
    )

    features_path = output_dir / "weekly_features.csv"
    risk_scores_path = output_dir / "latest_risk_scores.csv"
    write_csv_rows(features_path, feature_rows, WEEKLY_FEATURE_COLUMNS)
    write_csv_rows(risk_scores_path, risk_rows, RISK_SCORE_COLUMNS)

    print("Adding recall labels...", flush=True)
    labeled_rows = add_recall_labels(
        feature_rows,
        recalls,
        horizon_days=args.horizon_days,
        data_as_of_date=args.data_as_of_date,
    )
    trainable_rows = [row for row in labeled_rows if str(row.get("label_available")) == "1"]

    training_dataset_path = output_dir / "training_dataset.csv"
    trainable_dataset_path = output_dir / "training_dataset_labeled_only.csv"
    write_csv_rows(training_dataset_path, labeled_rows, TRAINING_DATASET_COLUMNS)
    write_csv_rows(trainable_dataset_path, trainable_rows, TRAINING_DATASET_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "built_at_utc": built_at_utc,
        "data_as_of_date": args.data_as_of_date,
        "horizon_days": args.horizon_days,
        "output_dir": display_path(output_dir),
        "weekly_features_csv": display_path(features_path),
        "latest_risk_scores_csv": display_path(risk_scores_path),
        "training_dataset_csv": display_path(training_dataset_path),
        "trainable_dataset_csv": display_path(trainable_dataset_path),
        "features": summarize_features(feature_rows, risk_rows),
        "labels": summarize_labeled_rows(labeled_rows),
    }

    summary_path = output_dir / "features_labels_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "backfill_features_labels_latest.md"
    write_markdown_report(summary, report_path)

    docs_result_path = DOCS_DIR / "BACKFILL_FEATURE_LABEL_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Feature rows:       {summary['features']['feature_row_count']}")
    print(f"Entity count:       {summary['features']['entity_count']}")
    print(f"Label-ready rows:   {summary['labels']['label_available_count']}")
    print(f"Positive rows:      {summary['labels']['positive_count']}")
    print(f"Positive rate:      {summary['labels']['positive_rate']}")
    print(f"Wrote:              {display_path(features_path)}")
    print(f"Wrote:              {display_path(training_dataset_path)}")
    print(f"Wrote:              {display_path(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
