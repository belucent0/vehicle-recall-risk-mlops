# Backfill Baseline Model Results

작성일: 2026-05-23 KST

## 할 작업

```text
Q2-1. pure Python logistic baseline을 scikit-learn baseline workflow로 교체
```

## 왜 하는가

기존 baseline은 직접 구현한 weighted logistic regression이었다. MVP 검증에는 충분했지만, 포트폴리오와 MLOps 관점에서는 일반적인 ML workflow와 거리가 있었다.

이번 단계의 목적은 다음과 같다.

```text
1. scikit-learn Pipeline 기반 baseline으로 교체한다.
2. StandardScaler / LogisticRegression / class_weight='balanced'를 명시한다.
3. joblib model artifact를 생성한다.
4. MLflow에 sklearn model artifact를 기록할 수 있게 한다.
5. Airflow E2E DAG에서 새 baseline이 끝까지 실행되는지 확인한다.
```

## 구현 파일

```text
src/recall_risk/models/baseline.py
pipelines/train_baseline_backfill.py
pipelines/train_baseline_sample.py
pipelines/log_baseline_mlflow.py
infra/airflow/requirements.txt
tests/test_baseline_model.py
```

## 모델 구성

현재 logistic baseline:

```text
scikit-learn Pipeline
-> SimpleImputer(strategy='constant', fill_value=0.0)
-> StandardScaler
-> LogisticRegression(class_weight='balanced', solver='lbfgs', max_iter=1000)
```

학습 데이터:

```text
positive 전체
negative downsampling
negative_ratio=20
max_train_rows=100000
actual train sample rows=57477
```

features:

```text
complaint_count
crash_count
fire_count
injury_count
death_count
severe_complaint_count
rolling_4w_complaint_mean_prior
rolling_8w_complaint_mean_prior
rolling_8w_complaint_std_prior
complaint_spike_z
baseline_risk_score
```

## 실행 명령

학습/평가:

```bash
python pipelines/train_baseline_backfill.py --run-id 20260515T114046Z --max-iter 1000 --negative-ratio 20 --max-train-rows 100000
```

MLflow 기록:

```bash
python pipelines/log_baseline_mlflow.py --run-id 20260515T114046Z
```

PostgreSQL 재적재:

```bash
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

Airflow E2E 재검증:

```bash
docker compose exec airflow-webserver airflow dags trigger nhtsa_recall_risk_mvp --run-id manual__sklearn_20260523T124600
```

## 결과 파일

```text
data/processed/backfill/20260515T114046Z/baseline_test_predictions.csv
data/processed/backfill/20260515T114046Z/baseline_logistic_coefficients.csv
data/processed/backfill/20260515T114046Z/baseline_model_summary.json
data/processed/backfill/20260515T114046Z/sklearn_logistic_pipeline.joblib
reports/backfill_baseline_model_latest.md
docs/BACKFILL_BASELINE_MODEL_RESULTS.md
```

`data/`, `models/`, `reports/`, `mlflow*.db`는 runtime artifact이므로 git에는 포함하지 않는다.

## Split

Split cutoff:

```text
2024-04-21
```

| Split | Rows | Positives | Positive rate | Date range |
|---|---:|---:|---:|---|
| train | 879,249 | 2,737 | 0.003113 | 2014-05-25 ~ 2024-04-21 |
| test | 293,083 | 1,611 | 0.005497 | 2024-04-21 ~ 2026-02-08 |

## Test metrics

| model | Average precision | Brier score | Precision@25 | Precision@50 | Precision@100 |
|---|---:|---:|---:|---:|---:|
| rule baseline | 0.006281 | 0.240245 | 0.080000 | 0.080000 | 0.040000 |
| sklearn logistic baseline | 0.008191 | 0.236554 | 0.000000 | 0.000000 | 0.000000 |

## 해석

1. Logistic baseline의 Average Precision은 rule baseline보다 약간 높다.
2. 하지만 Top-K 성능은 여전히 나쁘다. 상위 logistic score가 false positive에 몰린다.
3. score가 1.0에 가깝게 포화되는 케이스가 있으므로 calibration이 좋지 않다.
4. 따라서 현재 모델은 "최종 모델"이 아니라 MLOps 파이프라인 검증용 baseline이다.
5. 이번 단계의 핵심 성과는 성능 개선보다 **표준 ML workflow 전환과 artifact 추적 가능성 확보**다.

## MLflow 결과

로컬 MLflow run:

```text
tracking_uri: sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db
run_id: 0292a117bf854ce693d1720b1c76078d
status: FINISHED
```

Airflow MLflow run:

```text
tracking_uri: sqlite:////opt/airflow/project/mlflow_airflow.db
run_id: 7a669b81e7c84e40a9495dfa46522162
status: FINISHED
```

MLflow에 기록한 것:

```text
metrics 45개
baseline_model_summary.json
baseline_logistic_coefficients.csv
baseline metadata json
sklearn_logistic_pipeline.joblib
MLflow sklearn model artifact
```

## Airflow E2E 재검증

DAG:

```text
nhtsa_recall_risk_mvp
```

DAG run:

```text
manual__sklearn_20260523T124600
```

결과:

```text
state: success
execution_date: 2026-05-23T12:48:33+00:00
end_date: 2026-05-23T12:55:07+00:00
duration: about 6m 34s
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

## PostgreSQL / API 확인

PostgreSQL:

```text
baseline_test_predictions: 293083
baseline_logistic_coefficients: 12
```

FastAPI:

```text
GET /health/db: 200
GET /risk-scores/latest?limit=3: 200
```

## 결정

scikit-learn baseline 교체는 완료로 본다.

다음 모델 개선은 다음 중 하나다.

```text
1. calibration 개선
2. top-K ranking 개선
3. component/make/model matching 품질 개선
4. LightGBM/XGBoost 같은 tree-based model 비교
5. label leakage/temporal validation 추가 검증
```

