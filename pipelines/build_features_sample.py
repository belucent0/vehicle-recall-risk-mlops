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

from recall_risk.features.weekly_features import (  # noqa: E402
    RISK_SCORE_COLUMNS,
    WEEKLY_FEATURE_COLUMNS,
    add_rolling_features,
    aggregate_weekly_complaints,
    latest_week_scores,
    read_csv_rows,
    write_csv_rows,
)


INTERIM_SMOKE_DIR = PROJECT_ROOT / "data" / "interim" / "smoke_test"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "smoke_test"
REPORTS_DIR = PROJECT_ROOT / "reports"


def latest_run_dir() -> Path:
    candidates = [path for path in INTERIM_SMOKE_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No normalized smoke test run directory under {INTERIM_SMOKE_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build weekly features from normalized sample CSV.")
    parser.add_argument("--run-id", help="Smoke test run id. Defaults to latest normalized run.")
    parser.add_argument("--top-k", type=int, default=25)
    return parser.parse_args()


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
        "top_risk_rows": risk_rows[:10],
    }


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# Weekly Feature Sample Report",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Built at UTC: `{summary['built_at_utc']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Summary",
        "",
        f"- Feature rows: `{summary['features']['feature_row_count']}`",
        f"- Entity count: `{summary['features']['entity_count']}`",
        f"- Week range: `{summary['features']['min_week']} ~ {summary['features']['max_week']}`",
        f"- Non-zero complaint weeks: `{summary['features']['nonzero_feature_row_count']}`",
        "",
        "## Latest Week Top Risk Scores",
        "",
        "| Rank | Make | Model | Year | Component | Week | Complaints | Severe | Spike Z | Score |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]

    for row in summary["features"]["top_risk_rows"]:
        lines.append(
            f"| {row['rank']} | {row['make']} | {row['model']} | {row['model_year']} "
            f"| {row['component_primary']} | {row['week_start']} "
            f"| {row['complaint_count']} | {row['severe_complaint_count']} "
            f"| {row['complaint_spike_z']} | {row['baseline_risk_score']} |"
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_dir = INTERIM_SMOKE_DIR / args.run_id if args.run_id else latest_run_dir()
    if not source_dir.exists():
        raise FileNotFoundError(source_dir)

    run_id = source_dir.name
    complaints_path = source_dir / "complaints.csv"
    complaints = read_csv_rows(complaints_path)

    weekly_rows = aggregate_weekly_complaints(complaints)
    feature_rows = add_rolling_features(weekly_rows)
    built_at_utc = datetime.now(UTC).isoformat()
    risk_rows = latest_week_scores(
        feature_rows,
        top_k=args.top_k,
        source_run_id=run_id,
        scored_at_utc=built_at_utc,
    )

    output_dir = PROCESSED_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    features_path = output_dir / "weekly_features.csv"
    risk_scores_path = output_dir / "latest_risk_scores.csv"

    write_csv_rows(features_path, feature_rows, WEEKLY_FEATURE_COLUMNS)
    write_csv_rows(risk_scores_path, risk_rows, RISK_SCORE_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "built_at_utc": built_at_utc,
        "output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        "weekly_features_csv": str(features_path.relative_to(PROJECT_ROOT)),
        "latest_risk_scores_csv": str(risk_scores_path.relative_to(PROJECT_ROOT)),
        "features": summarize_features(feature_rows, risk_rows),
    }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "weekly_features_latest.md"
    write_markdown_report(summary, report_path)

    print(f"Feature rows: {summary['features']['feature_row_count']}")
    print(f"Entity count: {summary['features']['entity_count']}")
    print(f"Week range:   {summary['features']['min_week']} ~ {summary['features']['max_week']}")
    print(f"Wrote:        {features_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:        {risk_scores_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote:        {report_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
