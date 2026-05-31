# DAG Handoff Results

Written: 2026-05-31 KST

## Purpose

This document records the first verified Airflow handoff from the live NHTSA
collection DAG to the downstream processing/model DAG.

The verified flow:

```text
nhtsa_collect_incremental
  -> collect raw NHTSA snapshot
  -> validate manifest
  -> trigger nhtsa_recall_risk_mvp with conf.run_id
  -> normalize/features/train/report/load_postgres/log_mlflow
```

## Code changes

Updated DAGs:

```text
dags/nhtsa_collect_incremental.py
dags/nhtsa_recall_risk_mvp.py
```

### Collection DAG

Added downstream trigger task:

```text
trigger_recall_risk_mvp
```

It passes the generated collection run ID to the processing DAG:

```text
conf["run_id"] = collect_<airflow_ts_nodash>
conf["data_as_of_date"] = NHTSA_DATA_AS_OF_DATE fallback
```

### Processing DAG

Changed from fixed environment-based run ID to templated DAG conf:

```text
dag_run.conf["run_id"]
```

Fallback remains:

```text
NHTSA_RUN_ID or 20260515T114046Z
```

This keeps manual/local runs working while enabling automatic DAG-to-DAG
handoff.

## Local verification

Triggered collection DAG:

```powershell
docker compose exec airflow-webserver airflow dags trigger nhtsa_collect_incremental --run-id manual__handoff_20260531T170000
```

Collection DAG result:

```text
dag_id: nhtsa_collect_incremental
run_id: manual__handoff_20260531T170000
state: success
start_date: 2026-05-31T08:00:49.225078+00:00
end_date: 2026-05-31T08:01:12.279577+00:00
```

Generated collection run:

```text
run_id: collect_20260531T080049
vehicle count: 5
request count: 10
complaint records: 1655
recall records: 43
manifest rows: 10
```

Automatically triggered processing DAG:

```text
dag_id: nhtsa_recall_risk_mvp
run_id: process_collect_20260531T080049
state: success
start_date: 2026-05-31T08:01:12.242442+00:00
end_date: 2026-05-31T08:02:16.155349+00:00
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

## Processing output summary

For `collect_20260531T080049`:

| Metric | Value |
|---|---:|
| Complaints | 1,655 |
| Recalls | 43 |
| Weekly feature rows | 13,276 |
| Training dataset rows | 13,276 |
| Label-ready rows | 12,873 |
| Positive rows | 84 |
| Latest risk score rows | 2 |
| Baseline test prediction rows | 3,219 |
| Rule AP | 0.015402 |
| Logistic AP | 0.008436 |

API smoke after handoff load:

```text
GET /risk-scores/latest?limit=3: 200
top result: KIA TELLURIDE 2022 ELECTRICAL SYSTEM
```

After verification, local PostgreSQL serving tables were restored to the full
MVP backfill run:

```text
20260515T114046Z
```

Restored full serving counts:

| Table | Rows |
|---|---:|
| complaints | 103,440 |
| recalls | 3,018 |
| weekly_features | 1,189,569 |
| training_dataset | 1,189,569 |
| latest_risk_scores | 25 |
| baseline_test_predictions | 293,083 |

## Current caveat

The handoff is now real, but the downstream processing DAG still uses:

```text
load_postgres.py --apply-schema --truncate
```

That means every processing run replaces the current serving tables.

This is acceptable for the current MVP handoff verification, but it is not yet a
true incremental production ingestion design.

Next architectural fix:

```text
1. Add ingestion_state and raw_record_index tables.
2. Load new records incrementally instead of truncating all serving tables.
3. Store prediction rows with run_id and model_version.
```
