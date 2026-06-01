# Architecture ASCII Diagrams

Written: 2026-05-31 KST

This document visualizes the current and target architecture using plain ASCII
diagrams. It is meant to be readable in terminals, GitHub markdown, and code
review screens without Mermaid rendering.

Status note:

```text
As of 2026-05-31, collection-to-processing DAG handoff is implemented.
First-pass PostgreSQL ingestion_state/raw_record_index support is implemented.
Model/scoring version metadata is implemented in prediction and serving outputs.
Training and batch scoring are now separate pipeline scripts and Airflow tasks.
Model promotion gate is implemented before latest-week model score publishing.
The trained model now also produces latest-week serving scores.
The remaining major gap is connecting scoring to an MLflow model alias and
moving feature generation toward DB-backed bronze/silver tables.
```

## 1. Current architecture

The current project already has Airflow, PostgreSQL, FastAPI, MLflow, Docker,
and CI. The collection DAG now triggers the processing DAG with the generated
run_id.

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
|                    |  TriggerDagRunOperator                              |
|                    |  conf.run_id = generated collection run_id          |
|                    v                                                     |
|   +----------------------------------+                                   |
|   | DAG: nhtsa_recall_risk_mvp       |                                   |
|   | schedule: triggered/manual       |                                   |
|   | run_id source: dag_run.conf      |                                   |
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
|   |  train_model                     |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  score_batch                     |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  evaluate_model_gate             |                                   |
|   |          |                       |                                   |
|   |          v                       |                                   |
|   |  score_latest                    |                                   |
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
|    - model_promotion_decision.json                                       |
|    - model_latest_risk_scores.csv                                        |
|    - baseline_training_summary.json                                      |
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
|  model_latest_risk_scores                                                |
|  baseline_test_predictions                                               |
|  baseline_logistic_coefficients                                          |
|                                                                          |
|  view: v_latest_risk_scores                                              |
|  view: v_model_latest_risk_scores                                        |
+-------------------------------+------------------------------------------+
                                |
                                v
                    +---------------------------+
                    |          FastAPI          |
                    |                           |
                    |  GET /health              |
                    |  GET /health/db           |
                    |  GET /risk-scores/latest  |
                    |  GET /risk-scores/model/  |
                    |      latest               |
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

## 3. Near-term handoff architecture

This handoff has been implemented. The destructive truncate-based serving load
has also been removed from the default processing DAG path. Manual truncate is
still available for local reset.

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
              | -> score -> report -> load PG    |
              | -> MLflow                        |
              +----------------+-----------------+
                               |
                               v
              +----------------------------------+
              | PostgreSQL + FastAPI             |
              +----------------------------------+
```

Completed code changes:

```text
1. nhtsa_recall_risk_mvp reads dag_run.conf["run_id"].
2. Env var fallback remains for local/manual runs.
3. nhtsa_collect_incremental has final trigger_recall_risk_mvp task.
4. Verified processing run: process_collect_20260531T080049.
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
| automatic handoff  |
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
| Step 2 done        |
|                    |
| ingestion_state    |
| dedupe table       |
+---------+----------+
          |
          v
+--------------------+
| Step 3 done        |
|                    |
| separate training  |
| and scoring DAGs   |
+---------+----------+
          |
          v
+--------------------+
| Step 4 done        |
|                    |
| model promotion    |
| gate               |
+---------+----------+
          |
          v
+--------------------+
| Step 5 done        |
|                    |
| model latest       |
| serving scores     |
+---------+----------+
          |
          v
+--------------------+
| Step 6             |
|                    |
| MLflow registry    |
| promotion gate     |
+---------+----------+
          |
          v
+--------------------+
| Step 7             |
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
   |  automatic trigger with conf.run_id
   v
Airflow processing DAG
   |
   +--> normalize
   +--> feature/label build
   +--> train_model
   +--> score_batch        # held-out test evaluation
   +--> evaluate_model_gate
   +--> score_latest       # latest-week model serving score
   +--> load_postgres
   +--> log_mlflow
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

Connect scoring to an MLflow model artifact/alias,
then tighten promotion criteria and move features
toward DB-backed bronze/silver tables.


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
