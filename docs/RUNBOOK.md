# Local Runbook

작성일: 2026-05-23 KST

## 목적

이 문서는 로컬에서 현재 MVP 파이프라인과 서비스를 재실행/검증하는 절차를 정리한다.

대상:

```text
PostgreSQL
FastAPI
Airflow
MLflow logging
pytest
```

## 전제

필요 도구:

```text
Docker Desktop
Python 3.11+
PowerShell
```

현재 MVP의 중요한 전제:

```text
Airflow E2E DAG는 기존 raw backfill 데이터를 기준으로 재처리한다.
clean clone만으로는 data/ 이하 runtime artifact가 없으므로 전체 backfill 재현을 위해서는 collect_backfill 단계가 별도로 필요하다.
```

즉, 이 runbook은 현재 로컬 작업 디렉터리에 생성된 MVP artifact를 기준으로 검증하는 절차다.

## 1. Python 테스트

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

기대 결과:

```text
3 passed
```

## 2. PostgreSQL 실행

```powershell
docker compose up -d postgres
docker compose ps postgres
```

로컬 접속 정보:

```text
host: localhost
port: 55432
database: recall_risk
user: recall_user
password: recall_password
```

compose 내부 접속 정보:

```text
host: postgres
port: 5432
```

## 3. FastAPI 실행

```powershell
docker compose up -d api
docker compose ps api
```

기본 endpoint:

```text
http://localhost:28000
```

검증:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:28000/health
Invoke-WebRequest -UseBasicParsing http://localhost:28000/health/db
Invoke-WebRequest -UseBasicParsing "http://localhost:28000/risk-scores/latest?limit=3"
```

기대 결과:

```text
GET /health: 200
GET /health/db: 200
GET /risk-scores/latest?limit=3: 200
```

## 4. Airflow 실행

초기화:

```powershell
docker compose up airflow-init
```

webserver/scheduler 실행:

```powershell
docker compose up -d airflow-webserver airflow-scheduler
docker compose ps airflow-webserver airflow-scheduler
```

Airflow UI:

```text
http://localhost:18080
username: admin
password: admin
```

## 5. Airflow DAG 수동 실행

DAG:

```text
nhtsa_recall_risk_mvp
```

실행:

```powershell
docker compose exec airflow-webserver airflow dags unpause nhtsa_recall_risk_mvp
docker compose exec airflow-webserver airflow dags trigger nhtsa_recall_risk_mvp --run-id manual__local_check
```

상태 확인:

```powershell
docker compose exec airflow-webserver airflow dags list-runs -d nhtsa_recall_risk_mvp --no-backfill -o table
docker compose exec airflow-webserver airflow tasks states-for-dag-run nhtsa_recall_risk_mvp manual__local_check
```

기대 task 순서:

```text
check_project_files
normalize_backfill
build_features_labels
train_baseline
generate_latest_risk_report
load_postgres
log_mlflow
```

## 6. PostgreSQL row count 검증

```powershell
docker compose exec postgres psql -U recall_user -d recall_risk -c "
select 'complaints' as table_name, count(*) from recall_risk.complaints
union all select 'recalls', count(*) from recall_risk.recalls
union all select 'weekly_features', count(*) from recall_risk.weekly_features
union all select 'training_dataset', count(*) from recall_risk.training_dataset
union all select 'latest_risk_scores', count(*) from recall_risk.latest_risk_scores
union all select 'baseline_test_predictions', count(*) from recall_risk.baseline_test_predictions
order by table_name;
"
```

최근 검증값:

```text
baseline_test_predictions: 293083
complaints: 103440
latest_risk_scores: 25
recalls: 3018
training_dataset: 1189569
weekly_features: 1189569
```

## 7. MLflow 결과 확인

Airflow DAG는 다음 tracking URI를 사용한다.

```text
sqlite:////opt/airflow/project/mlflow_airflow.db
```

최근 검증된 run:

```text
run_id: b1a509073be84b19a886b51b53d24efe
status: FINISHED
logistic_average_precision: 0.008251
rule_average_precision: 0.006281
```

## 8. 현재 재현성 한계

```text
1. data/ 이하 runtime artifact는 git에 포함하지 않는다.
2. clean clone에서 즉시 Airflow E2E가 성공하려면 backfill data 생성 단계가 먼저 필요하다.
3. collect_backfill은 구현되어 있지만 Airflow E2E DAG에는 아직 포함하지 않았다.
4. NHTSA API 수집은 네트워크와 API 응답 상태에 영향을 받기 때문에 deterministic test와 분리하는 것이 맞다.
```

## 9. 다음 운영 개선

```text
1. small sample artifact 또는 deterministic fixture 추가
2. collect_backfill/incremental collector Airflow DAG 분리
3. CI에서 Docker build 검증 추가
4. MLflow model registry 또는 artifact store 정리
5. FastAPI OpenAPI 문서와 example response 정리
```

