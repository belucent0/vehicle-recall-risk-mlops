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
    read_csv_rows,
    summarize_labeled_rows,
    write_csv_rows,
)


INTERIM_SMOKE_DIR = PROJECT_ROOT / "data" / "interim" / "smoke_test"
PROCESSED_SMOKE_DIR = PROJECT_ROOT / "data" / "processed" / "smoke_test"
REPORTS_DIR = PROJECT_ROOT / "reports"


def latest_processed_run_dir() -> Path:
    candidates = [path for path in PROCESSED_SMOKE_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed smoke test run directory under {PROCESSED_SMOKE_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build labeled training dataset from sample features.")
    parser.add_argument("--run-id", help="Smoke test run id. Defaults to latest processed run.")
    parser.add_argument("--horizon-days", type=int, default=90)
    return parser.parse_args()


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    label = summary["labels"]
    lines = [
        "# Training Dataset Sample Report",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Horizon days: `{summary['horizon_days']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Label Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total rows | {label['row_count']} |",
        f"| Label available rows | {label['label_available_count']} |",
        f"| Label unavailable rows | {label['label_unavailable_count']} |",
        f"| Positive rows | {label['positive_count']} |",
        f"| Negative rows | {label['negative_count']} |",
        f"| Positive rate | {label['positive_rate']} |",
        f"| Positive entity count | {label['positive_entity_count']} |",
        f"| Max as-of date | {label['max_as_of_date']} |",
        f"| Max labeled as-of date | {label['max_labeled_as_of_date']} |",
        "",
        "## Top Positive Components",
        "",
        "| Component family | Positive rows |",
        "|---|---:|",
    ]

    for name, count in label["top_positive_components"]:
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `label_available=0` rows are too recent to know whether a recall happens within the full horizon.",
            "- The first MVP uses coarse `component_family` matching, e.g. `ELECTRICAL SYSTEM:SOFTWARE` -> `ELECTRICAL SYSTEM`.",
            "- This is a sample dataset from a small vehicle list, not yet a full historical backfill.",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    processed_run_dir = (
        PROCESSED_SMOKE_DIR / args.run_id if args.run_id else latest_processed_run_dir()
    )
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    interim_run_dir = INTERIM_SMOKE_DIR / run_id
    if not interim_run_dir.exists():
        raise FileNotFoundError(interim_run_dir)

    features_path = processed_run_dir / "weekly_features.csv"
    recalls_path = interim_run_dir / "recalls.csv"

    feature_rows = read_csv_rows(features_path)
    recall_rows = read_csv_rows(recalls_path)
    labeled_rows = add_recall_labels(
        feature_rows,
        recall_rows,
        horizon_days=args.horizon_days,
    )
    trainable_rows = [row for row in labeled_rows if str(row.get("label_available")) == "1"]

    training_dataset_path = processed_run_dir / "training_dataset.csv"
    trainable_dataset_path = processed_run_dir / "training_dataset_labeled_only.csv"

    write_csv_rows(training_dataset_path, labeled_rows, TRAINING_DATASET_COLUMNS)
    write_csv_rows(trainable_dataset_path, trainable_rows, TRAINING_DATASET_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "horizon_days": args.horizon_days,
        "output_dir": str(processed_run_dir.relative_to(PROJECT_ROOT)),
        "training_dataset_csv": str(training_dataset_path.relative_to(PROJECT_ROOT)),
        "trainable_dataset_csv": str(trainable_dataset_path.relative_to(PROJECT_ROOT)),
        "labels": summarize_labeled_rows(labeled_rows),
    }

    summary_path = processed_run_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "training_dataset_latest.md"
    write_markdown_report(summary, report_path)

    print(f"Rows total:        {summary['labels']['row_count']}")
    print(f"Rows label-ready:  {summary['labels']['label_available_count']}")
    print(f"Positive rows:     {summary['labels']['positive_count']}")
    print(f"Positive rate:     {summary['labels']['positive_rate']}")
    print(f"Wrote:             {training_dataset_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:             {trainable_dataset_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:             {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

