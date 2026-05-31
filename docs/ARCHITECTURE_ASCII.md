# Architecture ASCII Diagrams

Written: 2026-05-31 KST

This document visualizes the current and target architecture using plain ASCII
diagrams. It is meant to be readable in terminals, GitHub markdown, and code
review screens without Mermaid rendering.

## 1. Current architecture

The current project already has Airflow, PostgreSQL, FastAPI, MLflow, Docker,
and CI. The important gap is that the collection DAG and the processing DAG are
not automatically connected yet.

```text
                          +----------------------+
                          |      NHTSA APIs      |
                          | complaints / recalls |
                          +----------+-----------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                                  Airflow                                 |
|                                                                          |
|   +----------------------------------+                                   |
|   | DAG: nhtsa_collect_incremental   |                                   |
|   | schedule: @daily                 |                                   |
|   |                                  |                                   |
|   |  check_collection_inputs         |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  collect_nhtsa_snapshot          |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  validate_manifest               |                                   |
|   +----------------+-----------------+                                   |
|                    |                                                     |
|                    v                                                     |
|   +----------------------------------+                                   |
|   | data/raw/backfill/<run_id>/      |                                   |
|   | - raw JSON                       |                                   |
|   | - manifest.csv                   |                                   |
|   +----------------+-----------------+                                   |
|                    |                                                     |
|                    |  CURRENT GAP: manual run_id handoff                 |
|                    |  No automatic DAG-to-DAG trigger yet                |
|                    v                                                     |
|   +----------------------------------+                                   |
|   | DAG: nhtsa_recall_risk_mvp       |                                   |
|   | schedule: manual                 |                                   |
|   | current run_id source: env var   |                                   |
|   |                                  |                                   |
|   |  check_project_files             |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  normalize_backfill              |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  build_features_labels           |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  train_baseline                  |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  generate_latest_risk_report     |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  load_postgres                   |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  log_mlflow                      |                                   |
|   +----------+-----------------------+                                   |
+--------------|-----------------------------------------------------------+
               |
               v
+--------------------------------------------------------------------------+
|                           Local artifact layer                           |
|                                                                          |
|  data/interim/backfill/<run_id>/                                         |
|    - complaints.csv                                                      |
|    - recalls.csv                                                         |
|                                                                          |
|  data/processed/backfill/<run_id>/                                       |
|    - weekly_features.csv                                                 |
|    - training_dataset.csv                                                |
|    - latest_risk_scores.csv                                              |
|    - baseline_test_predictions.csv                                       |
|    - sklearn_logistic_pipeline.joblib                                    |
|                                                                          |
|  reports/*.md                                                            |
|  mlflow_airflow.db                                                       |
+-------------------------------+------------------------------------------+
                                |
                                v
+--------------------------------------------------------------------------+
|                         PostgreSQL: recall_risk                          |
|                                                                          |
|  backfill_manifest                                                       |
|  complaints                                                              |
|  recalls                                                                 |
|  weekly_features                                                         |
|  training_dataset                                                        |
|  latest_risk_scores                                                      |
|  baseline_test_predictions                                               |
|  baseline_logistic_coefficients                                          |
|                                                                          |
|  view: v_latest_risk_scores                                              |
+-------------------------------+------------------------------------------+
                                |
                                v
                    +---------------------------+
                    |          FastAPI          |
                    |                           |
                    |  GET /health              |
                    |  GET /health/db           |
                    |  GET /risk-scores/latest  |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | User / portfolio reviewer |
                    +---------------------------+
```

## 2. Current CI architecture

```text
+-------------------------+
| GitHub Actions: CI      |
+-----------+-------------+
            |
            v
  +-------------------+
  | checkout@v6       |
  +---------+---------+
            |
            v
  +-------------------+
  | setup-python@v6   |
  | Python 3.11       |
  +---------+---------+
            |
            v
  +-------------------+
  | install deps      |
  +---------+---------+
            |
            v
  +-------------------+
  | pytest            |
  +---------+---------+
            |
            v
  +-------------------+
  | DAG syntax check  |
  +---------+---------+
            |
            v
  +-------------------+
  | offline sample    |
  | E2E pipeline      |
  +---------+---------+
            |
            v
  +-------------------+
  | docker build api  |
  +---------+---------+
            |
            v
  +-------------------+
  | start PostgreSQL  |
  | load sample data  |
  +---------+---------+
            |
            v
  +-------------------+
  | start API         |
  | smoke test        |
  +-------------------+
```

## 3. Near-term target architecture

The next implementation should connect the collection DAG to the processing DAG.

```text
                          +----------------------+
                          |      NHTSA APIs      |
                          +----------+-----------+
                                     |
                                     v
              +----------------------------------+
              | DAG: nhtsa_collect_incremental   |
              |                                  |
              | 1. collect selected vehicles     |
              | 2. write raw JSON                |
              | 3. write manifest.csv            |
              | 4. validate manifest             |
              +----------------+-----------------+
                               |
                               v
              +----------------------------------+
              | generated run_id                 |
              | example: collect_20260525T171005 |
              +----------------+-----------------+
                               |
                               v
              +----------------------------------+
              | TriggerDagRunOperator            |
              | or Airflow Dataset scheduling    |
              |                                  |
              | pass conf:                       |
              |   {"run_id": generated_run_id}   |
              +----------------+-----------------+
                               |
                               v
              +----------------------------------+
              | DAG: nhtsa_recall_risk_mvp       |
              |                                  |
              | run_id source: dag_run.conf      |
              | not fixed env var                |
              +----------------+-----------------+
                               |
                               v
              +----------------------------------+
              | normalize -> features -> train   |
              | -> report -> load PG -> MLflow   |
              +----------------+-----------------+
                               |
                               v
              +----------------------------------+
              | PostgreSQL + FastAPI             |
              +----------------------------------+
```

Required code changes:

```text
1. Change nhtsa_recall_risk_mvp to read dag_run.conf["run_id"].
2. Keep env var fallback for local/manual runs.
3. Add final trigger task to nhtsa_collect_incremental.
4. Ensure the downstream run_id appears in logs, reports, and PostgreSQL metadata.
```

## 4. Target MLOps architecture

The final direction is to move from CSV-centered batch artifacts to a
stateful, incremental, DB-backed MLOps architecture.

```text
+------------------------------------------------------------------------------+
|                                  Sources                                     |
|                                                                              |
|  +------------------+   +------------------+   +-------------------------+   |
|  | NHTSA complaints |   | NHTSA recalls    |   | VPIC vehicle/model API  |   |
|  +--------+---------+   +--------+---------+   +-----------+-------------+   |
|           |                      |                         |                 |
+-----------|----------------------|-------------------------|-----------------+
            |                      |                         |
            v                      v                         v
+------------------------------------------------------------------------------+
|                            Airflow orchestration                              |
|                                                                              |
|  +------------------+     +------------------+     +----------------------+   |
|  | collection DAG   | --> | data quality DAG | --> | ingestion DAG        |   |
|  +--------+---------+     +--------+---------+     +----------+-----------+   |
|           |                        |                          |               |
|           v                        v                          v               |
|  +------------------+     +------------------+     +----------------------+   |
|  | feature DAG      | --> | training DAG     | --> | batch scoring DAG    |   |
|  +------------------+     +------------------+     +----------------------+   |
+------------------------------------------------------------------------------+
            |                        |                          |
            v                        v                          v
+------------------------------------------------------------------------------+
|                             Raw / replayable layer                            |
|                                                                              |
|  data/raw/<source>/<date>/<run_id>                                            |
|  manifest.csv                                                                |
|  immutable raw JSON snapshots                                                 |
+-----------------------------------+------------------------------------------+
                                    |
                                    v
+------------------------------------------------------------------------------+
|                         PostgreSQL analytical store                           |
|                                                                              |
|  ingestion_state                                                              |
|    - source                                                                   |
|    - cursor / query key                                                       |
|    - last_fetched_at                                                          |
|    - checksum                                                                 |
|                                                                              |
|  raw_record_index                                                             |
|    - source                                                                   |
|    - source_record_id                                                         |
|    - first_seen_run_id                                                        |
|    - latest_seen_run_id                                                       |
|                                                                              |
|  bronze tables                                                                |
|    - complaints                                                               |
|    - recalls                                                                  |
|                                                                              |
|  silver tables                                                                |
|    - weekly_features                                                          |
|    - label tables                                                             |
|                                                                              |
|  prediction tables                                                            |
|    - run_id                                                                   |
|    - model_version                                                            |
|    - score                                                                    |
|    - scored_at                                                                |
|                                                                              |
|  serving views                                                                |
|    - v_latest_risk_scores                                                     |
+-----------------------------------+------------------------------------------+
                                    |
                                    v
+------------------------------------------------------------------------------+
|                                ModelOps                                      |
|                                                                              |
|  +------------------+     +------------------+     +----------------------+   |
|  | scikit-learn     | --> | MLflow tracking  | --> | model registry       |   |
|  | later LightGBM   |     | metrics/artifacts|     | promotion gate       |   |
|  +------------------+     +------------------+     +----------------------+   |
|                                                                              |
|  Metrics: AP, recall@K, precision@K, calibration, backtest window             |
+-----------------------------------+------------------------------------------+
                                    |
                                    v
+------------------------------------------------------------------------------+
|                             Serving / consumption                             |
|                                                                              |
|  +------------------+     +------------------+     +----------------------+   |
|  | FastAPI          |     | dashboard        |     | alerts               |   |
|  | current          |     | later            |     | later                |   |
|  +------------------+     +------------------+     +----------------------+   |
+------------------------------------------------------------------------------+
                                    |
                                    v
+------------------------------------------------------------------------------+
|                                 Monitoring                                    |
|                                                                              |
|  data freshness                                                               |
|  source API failure rate                                                      |
|  row counts by run_id                                                         |
|  feature drift                                                                |
|  model quality by backtest window                                             |
|  API health / latency                                                         |
+------------------------------------------------------------------------------+
```

## 5. Migration path

```text
+--------------------+
| Current            |
|                    |
| collection DAG     |
| processing DAG     |
| manual handoff     |
+---------+----------+
          |
          v
+--------------------+
| Step 1             |
|                    |
| run_id conf        |
| DAG-to-DAG trigger |
+---------+----------+
          |
          v
+--------------------+
| Step 2             |
|                    |
| ingestion_state    |
| dedupe table       |
+---------+----------+
          |
          v
+--------------------+
| Step 3             |
|                    |
| separate training  |
| and scoring DAGs   |
+---------+----------+
          |
          v
+--------------------+
| Step 4             |
|                    |
| MLflow registry    |
| promotion gate     |
+---------+----------+
          |
          v
+--------------------+
| Step 5             |
|                    |
| monitoring         |
| dashboard / alerts |
+--------------------+
```

## 6. One-screen summary

```text
CURRENT
=======

NHTSA API
   |
   v
Airflow collection DAG
   |
   v
raw JSON + manifest
   |
   |  manual / not automated yet
   v
Airflow processing DAG
   |
   v
CSV artifacts
   |
   v
PostgreSQL
   |
   v
FastAPI


NEXT
====

NHTSA API
   |
   v
collection DAG
   |
   v
generated run_id
   |
   v
trigger processing DAG with conf.run_id
   |
   v
PostgreSQL + MLflow + FastAPI


TARGET
======

Sources
   |
   v
Collection -> DQ -> Incremental ingestion
   |
   v
PostgreSQL state + bronze/silver tables
   |
   v
Feature generation -> Training -> Scoring
   |
   v
MLflow registry + prediction tables
   |
   v
FastAPI / dashboard / monitoring
```
