# MLflow Connection Results

작성일: 2026-05-21 KST

## 목적

기존 MVP baseline 결과를 MLflow에 기록해서, 모델 실험 결과를 파일/문서만이 아니라 tracking store에서도 조회할 수 있게 만든다.

이번 단계는 재학습 자동화가 아니다. 이미 생성된 baseline 산출물을 MLflow에 기록하는 **최소 연결 단계**다.

## 구현 파일

```text
pipelines/log_baseline_mlflow.py
```

생성된 런타임 산출물:

```text
mlflow.db
models/baseline_logistic_20260515T114046Z.json
data/processed/backfill/20260515T114046Z/mlflow_baseline_run.json
```

`mlflow.db`, `mlruns/`, `models/*`, `data/processed/*`는 런타임 산출물이므로 `.gitignore` 대상이다.

## MLflow backend 결정

처음에는 local filesystem tracking URI를 시도했다.

```text
file:///C:/timblo/nhtsa-recall-risk-mlops/mlruns
```

하지만 MLflow 3.12.0에서 filesystem tracking backend deprecation warning이 발생했다.

따라서 기본 tracking URI를 SQLite backend로 변경했다.

```text
sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db
```

이 결정은 포트폴리오 관점에서도 더 낫다. 단순 파일 store보다 DB 기반 tracking store가 운영 구조에 가깝다.

## 실행한 명령

MLflow 설치:

```bash
python -m pip install "mlflow>=2.14.0"
```

dry-run:

```bash
python pipelines/log_baseline_mlflow.py --run-id 20260515T114046Z --dry-run
```

결과:

```text
Run ID:          20260515T114046Z
Tracking URI:    sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db
Experiment:      nhtsa-recall-risk
Run name:        baseline-20260515T114046Z
Metrics:         45
Artifacts:       4
Model artifact:  models\baseline_logistic_20260515T114046Z.json
Log predictions: False
Dry run only. No MLflow run was created.
```

SQLite backend 적용 후 실제 MLflow logging:

```bash
python pipelines/log_baseline_mlflow.py --run-id 20260515T114046Z
```

결과:

```text
Run ID:          20260515T114046Z
Tracking URI:    sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db
Experiment:      nhtsa-recall-risk
Run name:        baseline-20260515T114046Z
Metrics:         45
Artifacts:       4
Model artifact:  models\baseline_logistic_20260515T114046Z.json
Log predictions: False
MLflow run ID:   a4d29d2edaee414080dda8eefa3151eb
Wrote:           data\processed\backfill\20260515T114046Z\mlflow_baseline_run.json
```

## 기록된 MLflow 정보

Experiment:

```text
experiment_id: 1
name: nhtsa-recall-risk
```

Run:

```text
run_id: a4d29d2edaee414080dda8eefa3151eb
status: FINISHED
```

주요 metric:

| metric | value |
|---|---:|
| logistic_average_precision | 0.008251 |
| rule_average_precision | 0.006281 |
| logistic_brier_score | 0.103041 |
| test_row_count | 293083 |
| test_positive_count | 1611 |
| test_positive_rate | 0.005497 |

총 기록 metric 수:

```text
45
```

기록 artifact:

```text
data/processed/backfill/20260515T114046Z/baseline_model_summary.json
data/processed/backfill/20260515T114046Z/baseline_logistic_coefficients.csv
models/baseline_logistic_20260515T114046Z.json
reports/backfill_baseline_model_latest.md
```

큰 파일인 `baseline_test_predictions.csv`는 기본적으로 MLflow artifact에 올리지 않는다. 필요하면 다음 옵션을 사용한다.

```bash
python pipelines/log_baseline_mlflow.py --run-id 20260515T114046Z --log-predictions
```

## 조회 확인

실행:

```bash
python -c "import mlflow; mlflow.set_tracking_uri('sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db'); exp=mlflow.get_experiment_by_name('nhtsa-recall-risk'); print(exp.experiment_id, exp.name); runs=mlflow.search_runs([exp.experiment_id], max_results=5); print(runs[['run_id','status','metrics.logistic_average_precision','metrics.rule_average_precision']].to_string(index=False))"
```

결과:

```text
1 nhtsa-recall-risk
                          run_id   status  metrics.logistic_average_precision  metrics.rule_average_precision
a4d29d2edaee414080dda8eefa3151eb FINISHED                            0.008251                        0.006281
```

## MLflow UI 실행

PowerShell:

```powershell
python -m mlflow ui --backend-store-uri sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db --host 0.0.0.0 --port 5000
```

브라우저:

```text
http://localhost:5000
```

## 테스트 결과

전체 테스트:

```bash
$env:PYTHONPATH='src'
python -m pytest -q
```

결과:

```text
3 passed, 1 warning
```

warning은 기존 `baseline_score.py`의 pandas `FutureWarning`이며 이번 MLflow 작업과 직접 관련 없다.

## 현재 의미

완료된 것:

```text
기존 baseline 결과를 MLflow에 기록
SQLite tracking backend 생성
experiment/run/metrics/artifacts 조회 확인
모델 계수 artifact 생성
```

아직 안 한 것:

```text
학습 스크립트 내부에서 자동 MLflow logging
MLflow model registry
모델 promotion
Airflow DAG에서 MLflow logging 호출
```

## 결론

P3 MLflow 연결은 완료했다.

다음 작업은 **P4 Airflow DAG 전환**이다.

## 추가 검증: scikit-learn model logging

작성일: 2026-05-23 KST

baseline을 scikit-learn Pipeline으로 교체한 뒤 `pipelines/log_baseline_mlflow.py`에서 sklearn model artifact도 함께 기록하도록 변경했다.

새로 기록하는 artifact:

```text
sklearn_logistic_pipeline.joblib
MLflow sklearn model artifact: sklearn_model
baseline metadata json
baseline_model_summary.json
baseline_logistic_coefficients.csv
```

로컬 MLflow run:

```text
tracking_uri: sqlite:///C:/timblo/nhtsa-recall-risk-mlops/mlflow.db
run_id: 0292a117bf854ce693d1720b1c76078d
status: FINISHED
logistic_average_precision: 0.008191
rule_average_precision: 0.006281
```

Airflow MLflow run:

```text
tracking_uri: sqlite:////opt/airflow/project/mlflow_airflow.db
run_id: 7a669b81e7c84e40a9495dfa46522162
status: FINISHED
```
