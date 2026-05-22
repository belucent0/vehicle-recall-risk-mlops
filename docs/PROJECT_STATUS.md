# Project Status

작성일: 2026-05-22 KST

## 프로젝트

```text
Vehicle Recall Risk MLOps
```

## 목표

미국 NHTSA 공개 데이터를 이용해 차량/부품 단위의 리콜 위험 신호를 조기 감지하는 MVP를 만들고, 이후 MLOps 포트폴리오 구조로 확장한다.

## 현재 상태

```text
MVP complete
PostgreSQL load verified
FastAPI read API verified
MLflow baseline logging verified
Airflow DAG scaffold/smoke verified
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
Airflow: smoke done
Docker/CI: next
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

```text
experiment: nhtsa-recall-risk
metrics logged: 45
artifacts logged: 4
logistic_average_precision: 0.008251
rule_average_precision: 0.006281
```

상세 문서:

```text
docs/MLFLOW_CONNECTION_RESULTS.md
```

## Airflow DAG 결과

완료일: 2026-05-22 KST

Airflow UI:

```text
http://localhost:18080
admin / admin
```

DAG:

```text
nhtsa_recall_risk_mvp
```

검증:

```text
docker compose config: passed
Airflow image build: passed
airflow-init: passed
webserver/scheduler health: passed
DAG import: passed
check_project_files task test: SUCCESS
log_mlflow task test: SUCCESS
```

상세 문서:

```text
docs/AIRFLOW_DAG_RESULTS.md
```

## 현재 다음 작업

```text
P5. Docker/CI 정리
```

첫 범위:

```text
1. FastAPI Dockerfile 추가
2. docker-compose에 api 서비스 추가
3. GitHub Actions CI 추가
4. pytest 자동 실행
```

선택 작업:

```text
Airflow 전체 DAG end-to-end 실행
```

