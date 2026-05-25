# NHTSA Collection DAG Results

Written: 2026-05-26 KST

## Purpose

This document records the first verified scheduled data-collection DAG for the
Vehicle Recall Risk MLOps project.

The DAG is intentionally separated from the model-processing DAG. Its job is to
collect live NHTSA raw JSON snapshots for a small, controlled list of
vehicle-year targets and leave a manifest that downstream jobs can consume.

## Implemented files

```text
dags/nhtsa_collect_incremental.py
configs/nhtsa_collection_vehicles.csv
docker-compose.yml
.env.example
```

## DAG

```text
dag_id: nhtsa_collect_incremental
schedule: @daily
catchup: false
default vehicle limit: 5
```

Task order:

```text
check_collection_inputs
-> collect_nhtsa_snapshot
-> validate_manifest
```

The default collection target list is:

```text
FORD BRONCO SPORT 2022
HYUNDAI SANTA FE 2022
KIA TELLURIDE 2022
TESLA MODEL 3 2022
TOYOTA RAV4 2022
```

## Local verification

Command:

```powershell
docker compose exec airflow-webserver airflow dags trigger nhtsa_collect_incremental --run-id manual__collect_final_20260526T020000
docker compose exec airflow-webserver airflow dags list-runs -d nhtsa_collect_incremental --no-backfill -o table
```

Verified Airflow run:

```text
run_id: manual__collect_final_20260526T020000
state: success
execution_date: 2026-05-25T17:10:05+00:00
start_date: 2026-05-25T17:10:06.690403+00:00
end_date: 2026-05-25T17:10:18.864258+00:00
```

Generated collection run:

```text
run_id: collect_20260525T171005
raw output dir: data/raw/backfill/collect_20260525T171005
manifest: data/raw/backfill/collect_20260525T171005/manifest.csv
```

Summary:

| Metric | Value |
|---|---:|
| Vehicle count | 5 |
| Request count | 10 |
| Manifest rows | 10 |
| Complaint requests | 5 |
| Complaint non-empty responses | 5 |
| Complaint total records | 1,651 |
| Recall requests | 5 |
| Recall non-empty responses | 5 |
| Recall total records | 43 |

Endpoint status:

```text
complaints: {'200': 5}
recalls: {'200': 5}
```

## Interpretation

This verifies that Airflow can run the live data collection stage, call NHTSA
APIs, persist raw JSON files, and validate that a non-empty manifest was
created.

This is not yet a full record-level incremental ingestion system. It is a
scheduled snapshot collector for selected vehicle-year targets.

## Current limitations

```text
1. The collector re-fetches selected vehicle-year snapshots.
2. There is no record-level deduplication/state table yet.
3. The processing DAG does not automatically consume the newest collection run_id yet.
4. CI only checks DAG syntax. It does not call live NHTSA APIs.
```

## Next step

Connect the collection DAG to the processing DAG:

```text
1. Let nhtsa_recall_risk_mvp accept dag_run.conf["run_id"].
2. Trigger nhtsa_recall_risk_mvp after nhtsa_collect_incremental succeeds.
3. Later, add a Postgres ingestion state table for true incremental/dedup logic.
```
