from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from baseline_backfill_common import (  # noqa: E402
    DOCS_DIR,
    PROCESSED_BACKFILL_DIR,
    REPORTS_DIR,
    display_path,
    latest_run_dir,
    read_json,
    resolve_project_path,
    write_json,
)
from recall_risk.features.weekly_features import read_csv_rows, write_csv_rows  # noqa: E402
from recall_risk.models.baseline import (  # noqa: E402
    LOGISTIC_MODEL_VERSION,
    load_model_artifact,
    parse_float,
)


MODEL_LATEST_SCORING_METHOD = "sklearn_logistic_latest_week"

MODEL_LATEST_RISK_SCORE_COLUMNS = [
    "source_run_id",
    "model_version",
    "model_type",
    "model_library",
    "scoring_method",
    "scored_at_utc",
    "rank",
    "make",
    "model",
    "model_year",
    "component_primary",
    "week_start",
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
    "logistic_risk_score",
]


def latest_week_rows(rows: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    if not rows:
        return "", []
    latest_week = max(row["week_start"] for row in rows)
    return latest_week, [row for row in rows if row["week_start"] == latest_week]


def score_latest_rows(
    *,
    rows: list[dict[str, str]],
    run_id: str,
    model_artifact_path: Path,
    model_version: str,
    model_library: str,
    top_k: int,
    scored_at_utc: str,
) -> list[dict[str, Any]]:
    model = load_model_artifact(model_artifact_path)
    probabilities = model.predict_proba_rows(rows)

    scored_rows = []
    for row, probability in zip(rows, probabilities, strict=True):
        item = {column: row.get(column, "") for column in MODEL_LATEST_RISK_SCORE_COLUMNS}
        item["source_run_id"] = run_id
        item["model_version"] = model_version
        item["model_type"] = model.model_type
        item["model_library"] = model_library
        item["scoring_method"] = MODEL_LATEST_SCORING_METHOD
        item["scored_at_utc"] = scored_at_utc
        item["logistic_risk_score"] = round(float(probability), 8)
        scored_rows.append(item)

    scored_rows.sort(
        key=lambda row: (
            parse_float(row["logistic_risk_score"]),
            parse_float(row.get("baseline_risk_score")),
            parse_float(row.get("complaint_count")),
        ),
        reverse=True,
    )

    output = []
    for rank, row in enumerate(scored_rows[:top_k], start=1):
        item = dict(row)
        item["rank"] = rank
        output.append(item)
    return output


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# Model Latest Risk Score Results",
        "",
        f"- Source run ID: `{summary['source_run_id']}`",
        f"- Scored at UTC: `{summary['scored_at_utc']}`",
        f"- Latest week: `{summary['latest_week']}`",
        f"- Model version: `{summary['model_version']}`",
        f"- Model type: `{summary['model_type']}`",
        f"- Scoring method: `{summary['scoring_method']}`",
        f"- Model artifact: `{summary['model_artifact']}`",
        f"- Input CSV: `{summary['input_csv']}`",
        f"- Output CSV: `{summary['output_csv']}`",
        "",
        "## What changed",
        "",
        "The latest-week ranking below is produced by the trained scikit-learn logistic",
        "pipeline, not by the rule-only complaint spike score.",
        "",
        "## Top Model Risk Scores",
        "",
        "| Rank | Make | Model | Year | Component | Week | Complaints | Rule score | Logistic score |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|",
    ]

    for row in summary["top_rows"]:
        lines.append(
            f"| {row['rank']} | {row['make']} | {row['model']} | {row['model_year']} "
            f"| {row['component_primary']} | {row['week_start']} "
            f"| {row['complaint_count']} | {row['baseline_risk_score']} "
            f"| {row['logistic_risk_score']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a production-like batch scoring path for the trained model.",
            "- The logistic score is not yet calibrated as a real recall probability.",
            "- The endpoint should be treated as a ranking signal until calibration and backtesting improve.",
            "- The next step is to make scoring consume an MLflow model artifact or alias.",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score latest-week backfill rows with a trained model.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest processed backfill run.")
    parser.add_argument("--top-k", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_run_dir = PROCESSED_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    weekly_features_path = processed_run_dir / "weekly_features.csv"
    training_summary_path = processed_run_dir / "baseline_training_summary.json"
    output_path = processed_run_dir / "model_latest_risk_scores.csv"
    summary_path = processed_run_dir / "model_latest_risk_summary.json"

    if not training_summary_path.exists():
        raise FileNotFoundError(
            f"{display_path(training_summary_path)} is missing. "
            "Run pipelines/train_model_backfill.py first."
        )

    training_summary = read_json(training_summary_path)
    model_artifact_path = resolve_project_path(training_summary.get("model_artifact"))
    if model_artifact_path is None or not model_artifact_path.exists():
        raise FileNotFoundError(
            f"Model artifact is missing: {training_summary.get('model_artifact')}"
        )

    rows = read_csv_rows(weekly_features_path)
    latest_week, rows_to_score = latest_week_rows(rows)
    scored_at_utc = datetime.now(UTC).isoformat()
    model_version = training_summary.get("model_version", LOGISTIC_MODEL_VERSION)
    model_library = training_summary.get("model_library", "scikit-learn")

    risk_rows = score_latest_rows(
        rows=rows_to_score,
        run_id=run_id,
        model_artifact_path=model_artifact_path,
        model_version=model_version,
        model_library=model_library,
        top_k=args.top_k,
        scored_at_utc=scored_at_utc,
    )
    write_csv_rows(output_path, risk_rows, MODEL_LATEST_RISK_SCORE_COLUMNS)

    summary = {
        "source_run_id": run_id,
        "scored_at_utc": scored_at_utc,
        "latest_week": latest_week,
        "latest_week_row_count": len(rows_to_score),
        "top_k": args.top_k,
        "input_csv": display_path(weekly_features_path),
        "output_csv": display_path(output_path),
        "training_summary_json": display_path(training_summary_path),
        "model_artifact": display_path(model_artifact_path),
        "model_version": model_version,
        "model_type": risk_rows[0]["model_type"] if risk_rows else training_summary.get("model_type", ""),
        "model_library": model_library,
        "scoring_method": MODEL_LATEST_SCORING_METHOD,
        "top_rows": risk_rows,
    }
    write_json(summary_path, summary)

    report_path = REPORTS_DIR / "model_latest_risk_scores_latest.md"
    write_markdown_report(summary, report_path)

    docs_result_path = DOCS_DIR / "MODEL_LATEST_RISK_SCORE_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Latest week:      {latest_week}")
    print(f"Rows scored:      {len(rows_to_score)}")
    print(f"Rows output:      {len(risk_rows)}")
    print(f"Model version:    {model_version}")
    print(f"Wrote:            {display_path(output_path)}")
    print(f"Wrote:            {display_path(summary_path)}")
    print(f"Wrote:            {display_path(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
