# NHTSA Recall Risk MVP

미국 NHTSA 공개 데이터를 이용해 차량/부품 단위의 리콜 위험 신호를 조기 감지하는 MVP입니다.

현재 목표는 완성형 MLOps 배포가 아니라, 다음 end-to-end 흐름이 실제로 가능한지 검증하는 것입니다.

```text
NHTSA API 수집
  -> raw JSON 저장
  -> complaints/recalls 정규화
  -> weekly feature 생성
  -> 향후 90일 recall label 생성
  -> baseline 평가
  -> 최신 risk score report 생성
```

## Current MVP Result

기준 run:

```text
20260515T114046Z
```

| 항목 | 결과 |
|---|---:|
| MVP vehicle-year candidates | 917 |
| complaints rows | 103,440 |
| recalls rows | 3,018 |
| weekly feature rows | 1,189,569 |
| label-ready rows | 1,172,332 |
| positive rows | 4,348 |
| positive rate | 0.003709 |
| test positives | 1,611 |
| rule baseline AP | 0.006281 |
| logistic baseline AP | 0.008251 |
| latest risk week | 2026-05-11 |

## Interpretation

이 프로젝트는 아직 "리콜 확률을 정확히 예측하는 완성 모델"이 아닙니다.

현재 MVP의 의미는 다음과 같습니다.

```text
공식 NHTSA complaints/recalls 데이터를 이용해
차량/부품 단위로 리콜 조기경보용 dataset과 baseline score를 만들 수 있음을 검증했다.
```

`baseline_risk_score`는 리콜 확률이 아니라 complaint spike signal입니다.

## PostgreSQL Decision

2026-05-16 기준 기술스택 결정:

```text
PostgreSQL을 메인 저장소로 사용한다.
DuckDB는 도입하지 않는다.
```

PostgreSQL setup:

```bash
docker compose up -d postgres
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

기본 접속:

```text
host: localhost
port: 55432
database: recall_risk
user: recall_user
password: recall_password
```

## Reproduce MVP

### 1. Smoke cycle

```bash
python pipelines/collect_sample.py
python pipelines/normalize_sample.py
python pipelines/build_features_sample.py
python pipelines/build_training_dataset_sample.py
python pipelines/train_baseline_sample.py
```

### 2. MVP backfill

```bash
python pipelines/collect_vehicle_models.py
python pipelines/check_model_aliases_sample.py
python pipelines/collect_backfill.py --limit 50
python pipelines/filter_vehicle_models_mvp.py
python pipelines/collect_backfill.py --vehicle-models data/interim/vehicle_models_mvp.csv --limit 0
python pipelines/recover_backfill_manifest.py --run-id 20260515T114046Z
```

### 3. MVP dataset/model/report

```bash
python pipelines/normalize_backfill.py --run-id 20260515T114046Z
python pipelines/build_features_labels_backfill.py --run-id 20260515T114046Z --data-as-of-date 2026-05-15
python pipelines/train_baseline_backfill.py --run-id 20260515T114046Z --epochs 120 --negative-ratio 20 --max-train-rows 100000
python pipelines/generate_latest_risk_report.py --run-id 20260515T114046Z --top-k 25
```

## Main Outputs

```text
data/raw/backfill/20260515T114046Z/
data/interim/backfill/20260515T114046Z/complaints.csv
data/interim/backfill/20260515T114046Z/recalls.csv
data/processed/backfill/20260515T114046Z/weekly_features.csv
data/processed/backfill/20260515T114046Z/training_dataset.csv
data/processed/backfill/20260515T114046Z/baseline_test_predictions.csv
reports/latest_risk_score_report.md
```

## Documentation

핵심 문서:

```text
docs/MVP_SUMMARY.md
docs/MVP_CHECKLIST.md
docs/PROJECT_STATUS.md
docs/WORKFLOW.md
docs/BACKLOG.md
docs/TECH_STACK_DECISION.md
docs/POSTGRESQL_SETUP.md
docs/POSTGRESQL_LOAD_RESULTS.md
docs/FASTAPI_READ_API_RESULTS.md
docs/MLFLOW_CONNECTION_RESULTS.md
```

단계별 결과:

```text
docs/SMOKE_TEST_RESULTS.md
docs/NORMALIZATION_RESULTS.md
docs/WEEKLY_FEATURE_RESULTS.md
docs/TRAINING_DATASET_RESULTS.md
docs/BASELINE_MODEL_RESULTS.md
docs/VEHICLE_MODELS_RESULTS.md
docs/MODEL_ALIAS_RESULTS.md
docs/BACKFILL_COLLECTION_RESULTS.md
docs/BACKFILL_NORMALIZATION_RESULTS.md
docs/BACKFILL_FEATURE_LABEL_RESULTS.md
docs/BACKFILL_BASELINE_MODEL_RESULTS.md
docs/LATEST_RISK_SCORE_RESULTS.md
```

## Project Layout

```text
configs/                    Runtime/config files
data/                       Local generated data
docs/                       Project documentation
infra/postgres/             PostgreSQL schema/init files
pipelines/                  Step-by-step executable scripts
reports/                    Generated markdown reports
src/recall_risk/            Reusable package code
tests/                      Unit tests
```

## Current Limitations

```text
1. PostgreSQL 설정은 추가했지만 아직 Airflow/FastAPI와 연결하지 않았다.
2. component mapping이 거칠다.
3. F-150 등 일부 모델은 complaints endpoint coverage 이슈가 있다.
4. baseline model calibration이 약하다.
5. investigations / manufacturer communications 데이터를 아직 쓰지 않는다.
6. 최신 risk score는 리콜 확률이 아니라 complaint spike score다.
```

## Next Stack Steps

```text
1. PostgreSQL 적재 확인
2. FastAPI에서 PostgreSQL 조회
3. MLflow 연결
4. Airflow DAG 전환
5. Docker/CI 정리
```
