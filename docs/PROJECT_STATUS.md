# Project Status

작성일: 2026-05-21 KST

## 프로젝트

```text
NHTSA Recall Risk MLOps
```

## 목표

미국 NHTSA 공개 데이터를 이용해 차량/부품 단위의 리콜 위험 신호를 조기 감지하는 MVP를 만들고, 이후 MLOps 포트폴리오 구조로 확장한다.

## 현재 상태

```text
MVP complete
PostgreSQL stack selected
PostgreSQL load verified
FastAPI read API verified
MLflow baseline logging verified
```

## MVP 주요 결과

기준 run:

```text
20260515T114046Z
```

```text
unique vehicle-year count: 917
complaints rows: 103440
recalls rows: 3018
weekly feature rows: 1189569
label-ready rows: 1172332
positive rows: 4348
test positives: 1611
rule AP: 0.006281
logistic AP: 0.008251
latest risk week: 2026-05-11
```

## 기술스택 적용 상태

```text
PostgreSQL: done
FastAPI: done
MLflow: done
Airflow: next
Docker/CI: pending
```

## 주요 파일

```text
docker-compose.yml
configs/postgres.env.example
infra/postgres/initdb/001_schema.sql
pipelines/load_postgres.py
pipelines/log_baseline_mlflow.py
src/recall_risk/storage/postgres.py
src/recall_risk/serving/app.py
tests/test_serving_app.py
docs/POSTGRESQL_LOAD_RESULTS.md
docs/FASTAPI_READ_API_RESULTS.md
docs/MLFLOW_CONNECTION_RESULTS.md
```

## PostgreSQL 적재 결과

완료일: 2026-05-18 KST

```text
recall_risk.complaints: 103440
recall_risk.recalls: 3018
recall_risk.weekly_features: 1189569
recall_risk.training_dataset: 1189569
recall_risk.latest_risk_scores: 25
recall_risk.baseline_test_predictions: 293083
```

상세 문서:

```text
docs/POSTGRESQL_LOAD_RESULTS.md
```

## FastAPI 조회 API 결과

완료일: 2026-05-20 KST

Endpoint:

```text
GET /health
GET /health/db
GET /risk-scores/latest
```

검증:

```text
unit test: 2 passed
full test: 3 passed, 1 warning
actual DB smoke test: passed
```

상세 문서:

```text
docs/FASTAPI_READ_API_RESULTS.md
```

## MLflow 연결 결과

완료일: 2026-05-21 KST

Tracking URI:

```text
sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db
```

Experiment:

```text
nhtsa-recall-risk
```

Run:

```text
a4d29d2edaee414080dda8eefa3151eb
```

검증:

```text
metrics logged: 45
artifacts logged: 4
logistic_average_precision: 0.008251
rule_average_precision: 0.006281
```

상세 문서:

```text
docs/MLFLOW_CONNECTION_RESULTS.md
```

## 현재 다음 작업

```text
P4. Airflow DAG 전환
```

목표:

```text
기존 수집/정규화/feature/model/report/DB/MLflow 작업을 DAG 단위로 묶는다.
```

첫 범위:

```text
1. docker-compose에 Airflow 서비스 추가
2. dags/nhtsa_recall_risk_mvp.py 작성
3. PythonOperator 또는 BashOperator로 기존 pipeline script 호출
4. DAG smoke test
```

## 이후 순서

```text
P5. Docker/CI 정리
```

