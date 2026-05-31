# Train/Score Split Results

Written: 2026-06-01 KST

## Purpose

The backfill model pipeline no longer treats training and batch scoring as one
coupled step.

This matters operationally because MLOps usually separates:

```text
training:
  input features + labels
  -> trained model artifact
  -> training metadata / coefficients

batch scoring:
  input features
  + selected model artifact
  -> predictions
  -> scoring metadata / evaluation report
```

The project is still MVP-scale, but this change makes later work such as model
promotion, scheduled retraining, and scoring with a previously approved model
more realistic.

## Implemented flow

```text
data/processed/backfill/<run_id>/training_dataset_labeled_only.csv
        |
        v
pipelines/train_model_backfill.py
        |
        +--> sklearn_logistic_pipeline.joblib
        +--> baseline_logistic_coefficients.csv
        +--> baseline_training_summary.json
        |
        v
pipelines/score_batch_backfill.py
        |
        +--> baseline_test_predictions.csv
        +--> baseline_model_summary.json
        +--> reports/backfill_baseline_model_latest.md
        |
        v
pipelines/load_postgres.py
        |
        v
pipelines/log_baseline_mlflow.py
```

Airflow task order:

```text
check_project_files
  -> normalize_backfill
  -> build_features_labels
  -> train_model
  -> score_batch
  -> generate_latest_risk_report
  -> load_postgres
  -> log_mlflow
```

The old entrypoint remains as a compatibility wrapper:

```text
pipelines/train_baseline_backfill.py
  -> pipelines/train_model_backfill.py
  -> pipelines/score_batch_backfill.py
```

## Files changed

```text
src/recall_risk/models/baseline.py
  - added load_model_artifact()

pipelines/baseline_backfill_common.py
  - shared backfill utility functions

pipelines/train_model_backfill.py
  - trains sklearn logistic pipeline
  - writes model artifact, coefficients, and training summary

pipelines/score_batch_backfill.py
  - loads persisted model artifact
  - scores held-out temporal test rows
  - writes predictions, metrics, and final model summary

pipelines/train_baseline_backfill.py
  - compatibility wrapper around the split train/score scripts

dags/nhtsa_recall_risk_mvp.py
  - replaced train_baseline task with train_model and score_batch
```

## Direct script verification

Run ID:

```text
20260515T114046Z
```

Commands:

```powershell
python pipelines/train_model_backfill.py --run-id 20260515T114046Z --epochs 120 --negative-ratio 20 --max-train-rows 100000
python pipelines/score_batch_backfill.py --run-id 20260515T114046Z
```

Result:

```text
Train rows:       879249
Train positives:  2737
Test rows:        293083
Test positives:   1611
Sample rows:      57477
Rule AP:          0.006281
Logistic AP:      0.008191
```

MLflow compatibility:

```powershell
python pipelines/log_baseline_mlflow.py --run-id 20260515T114046Z --dry-run
```

Result:

```text
Metrics:         45
Artifacts:       5
Sklearn model:   data\processed\backfill\20260515T114046Z\sklearn_logistic_pipeline.joblib
Dry run only. No MLflow run was created.
```

## Airflow verification

Import/task check:

```text
airflow dags list-import-errors: No data found
airflow tasks list nhtsa_recall_risk_mvp:
  build_features_labels
  check_project_files
  generate_latest_risk_report
  load_postgres
  log_mlflow
  normalize_backfill
  score_batch
  train_model
```

Verified run:

```text
dag_id: nhtsa_recall_risk_mvp
run_id: manual__train_score_split_20260601T000200
state: success
start: 2026-05-31T15:23:02Z
end:   2026-05-31T15:29:27Z
duration: about 6m 25s
```

Task states:

```text
check_project_files: success
normalize_backfill: success
build_features_labels: success
train_model: success
score_batch: success
generate_latest_risk_report: success
load_postgres: success
log_mlflow: success
```

## Regression checks

```text
python -m py_compile ...: passed
python -m pytest -q: 4 passed
python pipelines/run_smoke_e2e.py --run-id ci_fixture --top-k 5 --max-iter 1000: passed
GET /health/db: {"status":"ok","database":"postgresql"}
```

PostgreSQL prediction metadata check:

```text
load_run_id        source_run_id       model_version       count
20260515T114046Z   20260515T114046Z    sklearn_logistic_v1 293083
```

## Current limitation

```text
Training and scoring are now separate scripts/tasks.
They are still part of the same processing DAG.
Feature generation still uses CSV artifacts.
There is not yet an MLflow model promotion gate or registry-backed scorer.
```

## Next

The next meaningful MLOps step is one of:

```text
1. make scoring load a selected MLflow model artifact / alias
2. add a model promotion gate based on AP, precision@K, and recall@K
3. move feature generation/loading closer to PostgreSQL bronze/silver tables
```
