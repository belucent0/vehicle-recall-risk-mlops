from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


PROCESSED_BACKFILL_DIR = PROJECT_ROOT / "data" / "processed" / "backfill"
REPORTS_DIR = PROJECT_ROOT / "reports"
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_EXPERIMENT_NAME = "nhtsa-recall-risk"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def default_tracking_uri() -> str:
    # MLflow 3.x deprecates the filesystem tracking backend.
    # Use a local SQLite backend by default while keeping artifacts on local disk.
    db_path = (PROJECT_ROOT / "mlflow.db").resolve().as_posix()
    return f"sqlite:///{db_path}"


def latest_run_dir() -> Path:
    candidates = [path for path in PROCESSED_BACKFILL_DIR.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No processed backfill run directory under {PROCESSED_BACKFILL_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def safe_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def safe_int(value: Any) -> int:
    return int(safe_float(value))


def collect_params(summary: dict[str, Any]) -> dict[str, Any]:
    split = summary["split"]
    sample = summary["logistic_training_sample"]
    return {
        "source_run_id": summary["source_run_id"],
        "input_dataset": summary["input_dataset"],
        "split_cutoff_as_of_date": split["cutoff_as_of_date"],
        "train_min_as_of_date": split["train"]["min_as_of_date"],
        "train_max_as_of_date": split["train"]["max_as_of_date"],
        "test_min_as_of_date": split["test"]["min_as_of_date"],
        "test_max_as_of_date": split["test"]["max_as_of_date"],
        "logistic_training_sample_rows": sample["row_count"],
        "model_type": summary.get("model_type", "sklearn_logistic_regression_pipeline"),
        "model_library": summary.get("model_library", "scikit-learn"),
        "label": "next_90d_recall",
    }


def collect_metrics(summary: dict[str, Any]) -> dict[str, float]:
    split = summary["split"]
    metrics: dict[str, float] = {
        "train_row_count": safe_float(split["train"]["row_count"]),
        "train_positive_count": safe_float(split["train"]["positive_count"]),
        "train_positive_rate": safe_float(split["train"]["positive_rate"]),
        "test_row_count": safe_float(split["test"]["row_count"]),
        "test_positive_count": safe_float(split["test"]["positive_count"]),
        "test_positive_rate": safe_float(split["test"]["positive_rate"]),
    }

    sample = summary["logistic_training_sample"]
    metrics.update(
        {
            "logistic_sample_row_count": safe_float(sample["row_count"]),
            "logistic_sample_positive_count": safe_float(sample["positive_count"]),
            "logistic_sample_positive_rate": safe_float(sample["positive_rate"]),
        }
    )

    for model_name, model_metrics in summary["test_metrics"].items():
        metrics[f"{model_name}_average_precision"] = safe_float(model_metrics["average_precision"])
        metrics[f"{model_name}_brier_score"] = safe_float(model_metrics["brier_score"])
        metrics[f"{model_name}_positive_rate"] = safe_float(model_metrics["positive_rate"])

        for item in model_metrics["precision_recall_at_k"]:
            k = safe_int(item["k"])
            metrics[f"{model_name}_precision_at_{k}"] = safe_float(item["precision"])
            metrics[f"{model_name}_recall_at_{k}"] = safe_float(item["recall"])
            metrics[f"{model_name}_hits_at_{k}"] = safe_float(item["hits"])

    return metrics


def write_model_artifact(
    *,
    run_id: str,
    summary: dict[str, Any],
    coefficients_path: Path,
) -> Path:
    coefficients = read_csv_dicts(coefficients_path)
    artifact = {
        "artifact_type": "baseline_model_metadata",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_run_id": run_id,
        "model_type": summary.get("model_type", "sklearn_logistic_regression_pipeline"),
        "model_library": summary.get("model_library", "scikit-learn"),
        "model_artifact": summary.get("model_artifact"),
        "label": "next_90d_recall",
        "note": "This artifact records baseline model metadata and coefficients. The sklearn pipeline is logged separately when available.",
        "metrics": summary["test_metrics"],
        "model_config": summary.get("model_config", {}),
        "coefficients": [
            {
                "feature": row["feature"],
                "coefficient": safe_float(row["coefficient"]),
            }
            for row in coefficients
        ],
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"baseline_logistic_{run_id}.json"
    model_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    return model_path


def resolve_project_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def log_to_mlflow(
    *,
    tracking_uri: str,
    experiment_name: str,
    run_name: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    artifact_paths: list[Path],
    sklearn_model_path: Path | None = None,
) -> str:
    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError(
            "MLflow is not installed. Install it with: python -m pip install \"mlflow>=2.14.0\""
        ) from exc

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name) as active_run:
        mlflow.set_tags(
            {
                "project": "nhtsa-recall-risk-mlops",
                "pipeline_stage": "baseline_model_evaluation",
                "data_source": "NHTSA",
            }
        )
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        for artifact_path in artifact_paths:
            if artifact_path.exists():
                mlflow.log_artifact(str(artifact_path))

        if sklearn_model_path and sklearn_model_path.exists():
            import joblib
            from mlflow import sklearn as mlflow_sklearn

            loaded = joblib.load(sklearn_model_path)
            sklearn_model = loaded["pipeline"] if isinstance(loaded, dict) else loaded
            mlflow_sklearn.log_model(
                sk_model=sklearn_model,
                artifact_path="sklearn_model",
            )

        return active_run.info.run_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log existing baseline outputs to MLflow.")
    parser.add_argument("--run-id", help="Processed backfill run id. Defaults to latest processed run.")
    parser.add_argument(
        "--tracking-uri",
        default=os.getenv("MLFLOW_TRACKING_URI", default_tracking_uri()),
        help="MLflow tracking URI. Defaults to local SQLite ./mlflow.db.",
    )
    parser.add_argument(
        "--experiment-name",
        default=os.getenv("MLFLOW_EXPERIMENT_NAME", DEFAULT_EXPERIMENT_NAME),
    )
    parser.add_argument("--run-name", help="MLflow run name. Defaults to baseline-{run_id}.")
    parser.add_argument(
        "--log-predictions",
        action="store_true",
        help="Also log the large baseline_test_predictions.csv artifact.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare params/metrics/artifacts without writing an MLflow run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_run_dir = PROCESSED_BACKFILL_DIR / args.run_id if args.run_id else latest_run_dir()
    if not processed_run_dir.exists():
        raise FileNotFoundError(processed_run_dir)

    run_id = processed_run_dir.name
    summary_path = processed_run_dir / "baseline_model_summary.json"
    coefficients_path = processed_run_dir / "baseline_logistic_coefficients.csv"
    predictions_path = processed_run_dir / "baseline_test_predictions.csv"
    model_latest_scores_path = processed_run_dir / "model_latest_risk_scores.csv"
    model_latest_summary_path = processed_run_dir / "model_latest_risk_summary.json"
    report_path = REPORTS_DIR / "backfill_baseline_model_latest.md"
    model_latest_report_path = REPORTS_DIR / "model_latest_risk_scores_latest.md"

    summary = read_json(summary_path)
    sklearn_model_path = resolve_project_path(summary.get("model_artifact"))
    params = collect_params(summary)
    metrics = collect_metrics(summary)
    model_artifact_path = write_model_artifact(
        run_id=run_id,
        summary=summary,
        coefficients_path=coefficients_path,
    )

    artifact_paths = [
        summary_path,
        coefficients_path,
        model_artifact_path,
        report_path,
    ]
    for optional_path in [
        model_latest_scores_path,
        model_latest_summary_path,
        model_latest_report_path,
    ]:
        if optional_path.exists():
            artifact_paths.append(optional_path)
    if sklearn_model_path and sklearn_model_path.exists():
        artifact_paths.append(sklearn_model_path)
    if args.log_predictions:
        artifact_paths.append(predictions_path)

    print(f"Run ID:          {run_id}")
    print(f"Tracking URI:    {args.tracking_uri}")
    print(f"Experiment:      {args.experiment_name}")
    print(f"Run name:        {args.run_name or f'baseline-{run_id}'}")
    print(f"Metrics:         {len(metrics)}")
    print(f"Artifacts:       {len(artifact_paths)}")
    print(f"Model artifact:  {display_path(model_artifact_path)}")
    print(
        "Sklearn model:   "
        f"{display_path(sklearn_model_path) if sklearn_model_path and sklearn_model_path.exists() else 'missing'}"
    )
    print(f"Log predictions: {args.log_predictions}")

    if args.dry_run:
        print("Dry run only. No MLflow run was created.")
        return 0

    mlflow_run_id = log_to_mlflow(
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name,
        run_name=args.run_name or f"baseline-{run_id}",
        params=params,
        metrics=metrics,
        artifact_paths=artifact_paths,
        sklearn_model_path=sklearn_model_path,
    )

    mlflow_result_path = processed_run_dir / "mlflow_baseline_run.json"
    mlflow_result = {
        "source_run_id": run_id,
        "mlflow_run_id": mlflow_run_id,
        "tracking_uri": args.tracking_uri,
        "experiment_name": args.experiment_name,
        "run_name": args.run_name or f"baseline-{run_id}",
        "logged_at_utc": datetime.now(UTC).isoformat(),
        "metrics_logged": sorted(metrics),
        "artifacts_logged": [display_path(path) for path in artifact_paths if path.exists()],
    }
    mlflow_result_path.write_text(json.dumps(mlflow_result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"MLflow run ID:   {mlflow_run_id}")
    print(f"Wrote:           {display_path(mlflow_result_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
