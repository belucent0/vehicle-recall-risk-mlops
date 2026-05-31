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
    PROCESSED_BACKFILL_DIR,
    display_path,
    latest_run_dir,
    sample_training_rows,
    split_summary,
    write_json,
)
from recall_risk.models.baseline import (  # noqa: E402
    COEFFICIENT_COLUMNS,
    LOGISTIC_MODEL_VERSION,
    coefficient_rows,
    labeled_rows,
    read_csv_rows,
    save_model_artifact,
    temporal_train_test_split,
    train_logistic_regression,
    write_csv_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a baseline model on a backfill dataset.")
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
    trained_at_utc = datetime.now(UTC).isoformat()
    model = train_logistic_regression(
        logistic_train_rows,
        epochs=args.epochs,
        max_iter=args.max_iter,
        random_state=args.seed,
    )

    coefficients_path = processed_run_dir / "baseline_logistic_coefficients.csv"
    model_artifact_path = processed_run_dir / "sklearn_logistic_pipeline.joblib"
    training_summary_path = processed_run_dir / "baseline_training_summary.json"

    write_csv_rows(
        coefficients_path,
        coefficient_rows(
            model,
            source_run_id=run_id,
            model_version=LOGISTIC_MODEL_VERSION,
            scored_at_utc=trained_at_utc,
        ),
        COEFFICIENT_COLUMNS,
    )
    save_model_artifact(model, model_artifact_path, model_version=LOGISTIC_MODEL_VERSION)

    summary = {
        "source_run_id": run_id,
        "pipeline_stage": "train_model",
        "trained_at_utc": trained_at_utc,
        "input_dataset": display_path(dataset_path),
        "training_summary_json": display_path(training_summary_path),
        "coefficients_csv": display_path(coefficients_path),
        "model_artifact": display_path(model_artifact_path),
        "model_type": model.model_type,
        "model_library": "scikit-learn",
        "model_version": LOGISTIC_MODEL_VERSION,
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
        "logistic_training_sample": split_summary(logistic_train_rows),
    }
    write_json(training_summary_path, summary)

    print(f"Train rows:       {summary['split']['train']['row_count']}")
    print(f"Train positives:  {summary['split']['train']['positive_count']}")
    print(f"Test rows:        {summary['split']['test']['row_count']}")
    print(f"Test positives:   {summary['split']['test']['positive_count']}")
    print(f"Sample rows:      {summary['logistic_training_sample']['row_count']}")
    print(f"Wrote:            {display_path(model_artifact_path)}")
    print(f"Wrote:            {display_path(coefficients_path)}")
    print(f"Wrote:            {display_path(training_summary_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
