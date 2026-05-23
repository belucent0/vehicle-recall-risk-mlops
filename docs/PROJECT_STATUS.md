# Project Status

작성일: 2026-05-23 KST

## 프로젝트

```text
Vehicle Recall Risk MLOps
```

## 현재 상태

```text
MVP complete
PostgreSQL load verified
FastAPI read API verified
MLflow baseline logging verified
Airflow DAG end-to-end run verified
Dockerized API verified
GitHub Actions CI added
```

## 핵심 결과

기준 데이터 run:

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
Airflow E2E: done
Docker API: done
GitHub Actions CI: added
Portfolio brief/runbook: done
```

## 주요 실행 포트

```text
PostgreSQL: localhost:55432
FastAPI container: http://localhost:28000
Airflow UI: http://localhost:18080
```

## Airflow E2E 결과

DAG:

```text
nhtsa_recall_risk_mvp
```

DAG run:

```text
manual__e2e_20260523T000000
```

결과:

```text
state: success
duration: about 7m 27s
```

전체 task:

```text
check_project_files: success
normalize_backfill: success
build_features_labels: success
train_baseline: success
generate_latest_risk_report: success
load_postgres: success
log_mlflow: success
```

상세 문서:

```text
docs/AIRFLOW_E2E_RUN_RESULTS.md
```

## 검증된 최종 산출

PostgreSQL:

```text
complaints: 103440
recalls: 3018
weekly_features: 1189569
training_dataset: 1189569
latest_risk_scores: 25
baseline_test_predictions: 293083
```

API:

```text
GET /health: 200
GET /health/db: 200
GET /risk-scores/latest?limit=3: 200
```

MLflow:

```text
run_id: b1a509073be84b19a886b51b53d24efe
status: FINISHED
logistic_average_precision: 0.008251
rule_average_precision: 0.006281
```

## 주요 결과 문서

```text
docs/PROJECT_OVERVIEW.md
docs/MVP_SUMMARY.md
docs/POSTGRESQL_LOAD_RESULTS.md
docs/FASTAPI_READ_API_RESULTS.md
docs/MLFLOW_CONNECTION_RESULTS.md
docs/AIRFLOW_DAG_RESULTS.md
docs/AIRFLOW_E2E_RUN_RESULTS.md
docs/DOCKER_CI_RESULTS.md
docs/PORTFOLIO_BRIEF.md
docs/RUNBOOK.md
```

## 현재 다음 작업 후보

이제 필수 MLOps scaffold와 공개 설명용 문서 초안은 end-to-end로 정리했다.

다음부터는 둘 중 하나를 선택한다.

### A. 모델/데이터 품질 개선

```text
scikit-learn baseline 교체
feature 개선
component matching 개선
label 누수/정합성 추가 검증
MLflow model artifact 정교화
```

### B. 재현성/운영성 개선

```text
clean clone에서 small sample E2E 가능하게 fixture 추가
collect_backfill/incremental collector Airflow DAG 분리
CI에서 Docker build 검증 추가
GitHub Actions 원격 green 확인
```
