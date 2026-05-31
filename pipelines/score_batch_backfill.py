from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path


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
    top_predictions,
    write_json,
    write_markdown_report,
)
from recall_risk.models.baseline import (  # noqa: E402
    LOGISTIC_MODEL_VERSION,
    PREDICTION_COLUMNS,
    evaluate_scores,
    labeled_rows,
    load_model_artifact,
    read_csv_rows,
    score_rows,
    temporal_train_test_split,
    write_csv_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score a held-out backfill batch with a trained model.")
    parser.add_argument("--run-id", help="Backfill run id. Defaults to latest processed backfill run.")
    parser.add_argument("--top-predictions", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_run_dir = PROCESSED_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    dataset_path = processed_run_dir / "training_dataset_labeled_only.csv"
    training_summary_path = processed_run_dir / "baseline_training_summary.json"
    predictions_path = processed_run_dir / "baseline_test_predictions.csv"
    final_summary_path = processed_run_dir / "baseline_model_summary.json"

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

    print("Reading labeled dataset...", flush=True)
    rows = labeled_rows(read_csv_rows(dataset_path))
    _, test_rows, cutoff_date = temporal_train_test_split(rows)
    expected_cutoff_date = training_summary["split"]["cutoff_as_of_date"]
    if cutoff_date != expected_cutoff_date:
        raise RuntimeError(
            "Temporal split changed between training and scoring: "
            f"expected {expected_cutoff_date}, got {cutoff_date}"
        )

    print(f"Loading model artifact: {display_path(model_artifact_path)}", flush=True)
    model = load_model_artifact(model_artifact_path)

    print(f"Scoring {len(test_rows)} test rows...", flush=True)
    scored_at_utc = datetime.now(UTC).isoformat()
    model_version = training_summary.get("model_version", LOGISTIC_MODEL_VERSION)
    test_predictions = score_rows(
        test_rows,
        model,
        "test",
        source_run_id=run_id,
        model_version=model_version,
        scored_at_utc=scored_at_utc,
        model_library=training_summary.get("model_library", "scikit-learn"),
    )
    write_csv_rows(predictions_path, test_predictions, PREDICTION_COLUMNS)

    final_summary = dict(training_summary)
    final_summary.update(
        {
            "pipeline_stage": "score_batch",
            "built_at_utc": scored_at_utc,
            "scored_at_utc": scored_at_utc,
            "training_summary_json": display_path(training_summary_path),
            "predictions_csv": display_path(predictions_path),
            "test_metrics": {
                "rule": evaluate_scores(test_predictions, "rule_score"),
                "logistic": evaluate_scores(test_predictions, "logistic_score"),
            },
            "top_logistic_predictions": top_predictions(
                test_predictions,
                "logistic_score",
                limit=args.top_predictions,
            ),
        }
    )
    write_json(final_summary_path, final_summary)

    report_path = REPORTS_DIR / "backfill_baseline_model_latest.md"
    write_markdown_report(final_summary, report_path)

    docs_result_path = DOCS_DIR / "BACKFILL_BASELINE_MODEL_RESULTS.md"
    docs_result_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Test rows:        {final_summary['split']['test']['row_count']}")
    print(f"Test positives:   {final_summary['split']['test']['positive_count']}")
    print(f"Rule AP:          {final_summary['test_metrics']['rule']['average_precision']}")
    print(f"Logistic AP:      {final_summary['test_metrics']['logistic']['average_precision']}")
    print(f"Wrote:            {display_path(predictions_path)}")
    print(f"Wrote:            {display_path(final_summary_path)}")
    print(f"Wrote:            {display_path(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
