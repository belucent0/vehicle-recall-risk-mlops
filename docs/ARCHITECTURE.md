# Architecture

## 현재 단계

현재는 전체 MLOps 아키텍처를 모두 구현하는 단계가 아니라 **smoke test** 단계다.

목표:

1. NHTSA API가 실제로 호출되는지 확인
2. complaints/recalls 응답 스키마 확인
3. raw JSON 저장
4. 정규화 가능한 핵심 필드 파악

이 단계에서는 Airflow, MLflow, dashboard, serving API를 본격 구현하지 않는다.

## Target Architecture

```text
NHTSA APIs
  ├─ complaints
  ├─ recalls
  ├─ investigations          later
  └─ manufacturer comms      later
        │
        ▼
Ingestion Jobs
  ├─ daily incremental collector
  └─ historical backfill collector
        │
        ▼
Raw Data Layer
  └─ data/raw/*.json
        │
        ▼
Normalization Layer
  ├─ complaints table
  ├─ recalls table
  └─ vehicle/model dimension tables
        │
        ▼
Feature Layer
  ├─ weekly complaint counts
  ├─ rolling averages
  ├─ spike z-scores
  ├─ severity keyword features
  └─ component-level history
        │
        ▼
Label Layer
  └─ recall within next 90 days
        │
        ▼
Model / Scoring Layer
  ├─ baseline rule score
  ├─ logistic regression / tree model
  └─ batch inference
        │
        ▼
Serving / Reporting
  ├─ risk score table
  ├─ FastAPI endpoint
  ├─ dashboard
  └─ alert
```

## MVP Architecture

MVP에서는 아래까지만 구현한다.

```text
NHTSA API
  ▼
collect_sample.py
  ▼
data/raw/*.json
  ▼
normalize.py
  ▼
data/interim/*.parquet or duckdb tables
  ▼
build_features.py
  ▼
weekly entity features
  ▼
baseline_score.py
  ▼
risk scores
```

## Later MLOps Architecture

MVP가 성공한 뒤 다음 도구를 붙인다.

- Orchestration: Prefect or Airflow
- Storage: DuckDB first, Postgres later
- Experiment tracking: MLflow
- Data/version tracking: DVC or lakeFS
- API serving: FastAPI
- Monitoring: Grafana/Prometheus or simple dashboard first
- CI: GitHub Actions

## Design Principle

먼저 "한 번 도는 파이프라인"을 만든다.

그다음 반복적으로 다음을 붙인다.

1. 재현성
2. 스케줄링
3. 모델 실험 관리
4. 모니터링
5. API/대시보드

처음부터 완성형 아키텍처를 구현하지 않는다.

