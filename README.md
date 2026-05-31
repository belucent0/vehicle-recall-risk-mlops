# Vehicle Recall Risk MLOps

> Work in progress.

미국 NHTSA 공개 데이터를 시작점으로 차량 리콜 위험 신호를 조기 감지하고, 이를 MLOps 파이프라인으로 운영화하는 프로젝트입니다.

현재 README는 임시 진입점으로만 관리합니다. 상세한 진행 내용과 의사결정은 `docs/` 아래 문서에 기록합니다.

## Current status

```text
MVP data/model cycle: done
PostgreSQL load: done
FastAPI read API: done
MLflow logging: done
Airflow DAG scaffold: done
Airflow E2E run: done
scikit-learn baseline: done
Docker API: done
GitHub Actions CI: green
CI PostgreSQL/API smoke: added
NHTSA scheduled collection DAG: verified
```

## Quick links

```text
docs/PROJECT_OVERVIEW.md
docs/PROJECT_STATUS.md
docs/BACKLOG.md
docs/ARCHITECTURE_VISUALIZATION.md
docs/ARCHITECTURE_ASCII.md
docs/DAG_HANDOFF_RESULTS.md
docs/INCREMENTAL_INGESTION_RESULTS.md
docs/MODEL_VERSION_METADATA_RESULTS.md
docs/PORTFOLIO_BRIEF.md
docs/RUNBOOK.md
docs/REPRODUCIBILITY_RESULTS.md
docs/NHTSA_COLLECTION_DAG_RESULTS.md
docs/MVP_SUMMARY.md
docs/POSTGRESQL_LOAD_RESULTS.md
docs/FASTAPI_READ_API_RESULTS.md
docs/MLFLOW_CONNECTION_RESULTS.md
docs/AIRFLOW_DAG_RESULTS.md
docs/AIRFLOW_E2E_RUN_RESULTS.md
docs/DOCKER_CI_RESULTS.md
```

## Local commands

PostgreSQL:

```bash
docker compose up -d postgres
```

FastAPI:

```bash
docker compose up -d api
```

API endpoint:

```text
http://localhost:28000
```

Tests:

```bash
$env:PYTHONPATH='src'
python -m pytest -q
```

Offline sample E2E:

```bash
python pipelines/run_smoke_e2e.py --run-id ci_fixture
```

Load offline sample into PostgreSQL:

```bash
python pipelines/load_postgres.py --dataset smoke_test --run-id ci_fixture --apply-schema --truncate
```

## Note

This repository is intentionally evolving. The README will be rewritten after the MVP MLOps flow is stable.
