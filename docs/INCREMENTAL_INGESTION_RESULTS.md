# Incremental PostgreSQL Ingestion Results

Written: 2026-05-31 KST

## Purpose

This document records the first PostgreSQL ingestion-state implementation for
the Vehicle Recall Risk MLOps project.

The goal was to reduce dependence on:

```text
load_postgres.py --truncate
```

and introduce enough state to support repeatable non-destructive loads.

## Implemented files

```text
infra/postgres/initdb/001_schema.sql
pipelines/load_postgres.py
dags/nhtsa_recall_risk_mvp.py
```

## Schema additions

New state tables:

```text
recall_risk.ingestion_state
recall_risk.raw_record_index
```

Metadata columns added to load targets:

```text
load_run_id
loaded_at_utc
record_hash
```

The loader now tracks per-table ingestion state:

```text
table_name
load_run_id
dataset
source_path
status
row_count
inserted_count
skipped_count
started_at_utc
completed_at_utc
```

## Loader behavior

`pipelines/load_postgres.py` now:

```text
1. Builds a temporary CSV with load_run_id, loaded_at_utc, record_hash.
2. Loads that CSV into a temporary PostgreSQL table.
3. Inserts into the target table with ON CONFLICT DO NOTHING.
4. Records table-level success/failure in ingestion_state.
5. Skips a table if the same table_name + load_run_id already succeeded.
6. Tracks raw record hashes for backfill_manifest, complaints, and recalls.
```

Current dedupe behavior:

```text
All tables:
  - duplicate table_name + load_run_id + record_hash is skipped

Complaints and recalls:
  - duplicate record_hash is skipped across runs

Raw record index:
  - maintained for backfill_manifest, complaints, recalls
```

## DAG change

The processing DAG no longer truncates serving tables by default.

Before:

```text
python pipelines/load_postgres.py --run-id <run_id> --apply-schema --truncate
```

After:

```text
python pipelines/load_postgres.py --run-id <run_id> --apply-schema
```

Manual reset is still possible:

```powershell
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

## Local smoke verification

Command:

```powershell
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema --truncate
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema
```

First load:

```text
complaints: inserted=30 skipped=0
recalls: inserted=4 skipped=0
weekly_features: inserted=77 skipped=0
training_dataset: inserted=77 skipped=0
training_dataset_labeled_only: inserted=73 skipped=0
latest_risk_scores: inserted=2 skipped=0
baseline_test_predictions: inserted=73 skipped=0
baseline_logistic_coefficients: inserted=12 skipped=0
```

Second load with same `run_id`:

```text
SKIP already ingested
```

State counts after smoke verification:

```text
ingestion_state: 8
raw_record_index: 34
```

## Airflow verification

Verified that `nhtsa_recall_risk_mvp` can run with the non-truncating load step.

Run:

```text
dag_id: nhtsa_recall_risk_mvp
run_id: manual__incremental_default_20260531T173500
state: success
```

Task states:

```text
check_project_files: success
normalize_backfill: success
build_features_labels: success
train_baseline: success
generate_latest_risk_report: success
load_postgres: success
log_mlflow: success
```

## Full MVP restore

After verification, local PostgreSQL was reset to the full MVP run with:

```powershell
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

Result:

| Table | Rows |
|---|---:|
| complaints | 101,163 |
| recalls | 3,018 |
| weekly_features | 1,189,569 |
| training_dataset | 1,189,569 |
| latest_risk_scores table | 25 |
| v_latest_risk_scores view | 25 |
| raw_record_index | 106,015 |
| ingestion_state | 9 |

Note:

```text
complaints source CSV rows: 103,440
complaints inserted rows: 101,163
skipped exact duplicate complaint rows: 2,277
```

The API still returns the expected top full-MVP risk scores through the latest
successful `latest_risk_scores` load:

```text
GET /risk-scores/latest?limit=3: 200
```

Top result:

```text
FORD BRONCO SPORT 2021 UNKNOWN OR OTHER
```

## Current limitation

This is not yet a full production-grade incremental warehouse.

Remaining gaps:

```text
1. Feature generation still starts from CSV artifacts, not from PostgreSQL bronze tables.
2. The loader appends derived tables by run_id instead of maintaining compact latest-only tables.
3. There is no model_version column in prediction outputs yet.
4. raw_record_index is hash-based, not source-key based for every endpoint.
```

Next step:

```text
Add run_id/model_version metadata to prediction tables and serving views,
then split training and scoring as separate DAG stages.
```
