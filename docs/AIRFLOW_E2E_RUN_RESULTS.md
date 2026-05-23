# Airflow E2E Run Results

작성일: 2026-05-23 KST

## 목적

Airflow DAG를 smoke test 수준이 아니라 전체 end-to-end로 한 번 실행해, 데이터/모델/적재/실험기록 파이프라인이 orchestration되는지 확인한다.

## 실행 대상

DAG:

```text
nhtsa_recall_risk_mvp
```

DAG run:

```text
manual__e2e_20260523T000000
```

기준 데이터 run:

```text
20260515T114046Z
```

## 실행 명령

```bash
docker compose exec airflow-webserver airflow dags unpause nhtsa_recall_risk_mvp
docker compose exec airflow-webserver airflow dags trigger nhtsa_recall_risk_mvp --run-id manual__e2e_20260523T000000
```

상태 확인:

```bash
docker compose exec airflow-webserver airflow dags list-runs -d nhtsa_recall_risk_mvp --no-backfill -o table
docker compose exec airflow-webserver airflow tasks states-for-dag-run nhtsa_recall_risk_mvp manual__e2e_20260523T000000
```

## DAG run 결과

```text
state: success
execution_date: 2026-05-23T06:37:47+00:00
start_date: 2026-05-23T06:37:47.491276+00:00
end_date: 2026-05-23T06:45:14.375409+00:00
duration: about 7m 27s
```

## Task 결과

| task | state | start UTC | end UTC | duration |
|---|---|---|---|---:|
| check_project_files | success | 06:37:48 | 06:37:49 | ~1s |
| normalize_backfill | success | 06:37:51 | 06:39:00 | ~1m 9s |
| build_features_labels | success | 06:39:02 | 06:42:26 | ~3m 24s |
| train_baseline | success | 06:42:28 | 06:43:50 | ~1m 22s |
| generate_latest_risk_report | success | 06:43:51 | 06:43:53 | ~1s |
| load_postgres | success | 06:43:54 | 06:44:55 | ~1m 1s |
| log_mlflow | success | 06:44:57 | 06:45:13 | ~16s |

## PostgreSQL 검증

Airflow DAG 실행 후 주요 테이블 row count를 직접 확인했다.

```text
baseline_test_predictions: 293083
complaints: 103440
latest_risk_scores: 25
recalls: 3018
training_dataset: 1189569
weekly_features: 1189569
```

## API 검증

실행:

```text
GET http://localhost:28000/risk-scores/latest?limit=3
```

결과:

```text
HTTP 200
```

상위 응답:

| rank | make | model | model_year | component | week_start | score |
|---:|---|---|---:|---|---|---:|
| 1 | FORD | BRONCO SPORT | 2021 | UNKNOWN OR OTHER | 2026-05-11 | 2.8062 |
| 2 | FORD | BRONCO SPORT | 2022 | ENGINE | 2026-05-11 | 2.4749 |
| 3 | FORD | ESCAPE | 2015 | POWER TRAIN | 2026-05-11 | 2.4749 |

## MLflow 검증

Airflow DAG의 `log_mlflow` task가 새 MLflow run을 생성했다.

```text
tracking_uri: sqlite:////opt/airflow/project/mlflow_airflow.db
experiment: nhtsa-recall-risk
run_id: b1a509073be84b19a886b51b53d24efe
status: FINISHED
```

주요 metric:

| metric | value |
|---|---:|
| logistic_average_precision | 0.008251 |
| rule_average_precision | 0.006281 |
| test_row_count | 293083 |

## 현재 의미

이제 다음 문장을 포트폴리오에 쓸 수 있다.

```text
The full MVP pipeline is orchestrated and verified through Airflow:
normalize -> feature/label build -> baseline training -> risk report -> PostgreSQL load -> MLflow logging.
```

한국어로는:

```text
정규화, feature/label 생성, baseline 학습, 최신 risk report 생성, PostgreSQL 적재, MLflow 기록까지 Airflow DAG로 end-to-end 실행을 검증했다.
```

## 남은 한계

```text
1. 전체 DAG는 아직 schedule 기반 자동 반복 운영까지 검증하지 않았다.
2. 데이터 수집 collect_backfill은 이번 DAG에 포함하지 않았다. 기존 raw backfill 데이터를 기준으로 재처리했다.
3. 모델은 아직 baseline 수준이다.
4. GitHub Actions 원격 실행 결과는 별도 확인이 필요하다.
```

## 결론

Airflow 전체 DAG end-to-end 실행은 성공했다.

MVP 기준 MLOps scaffold는 이제 다음 순서까지 검증됐다.

```text
PostgreSQL
FastAPI
MLflow
Airflow E2E
Docker API
GitHub Actions CI scaffold
```

