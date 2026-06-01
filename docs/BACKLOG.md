# Backlog

MVP와 MLOps scaffold는 end-to-end로 한 사이클 완료했다.

## 현재 완료 상태

```text
S0 프로젝트 구조 생성: done
S1 NHTSA API smoke test: done
S2 Raw JSON 정규화: done
S3 Weekly feature 생성: done
S4 90일 recall label 생성: done
S5 Baseline model 평가: done
M1 VPIC vehicle model list 수집: done
M2 모델명 alias/정규화 확인: done
M3 Backfill collector 구현: done
M4 Backfill 대상 vehicle model 후보 정제: done
M5 MVP 후보 vehicle backfill 수집 실행: done
M6 Backfill 정규화: done
M7 Backfill feature/label 생성: done
M8 Backfill baseline 재평가: done
M9 최신 risk score 리포트 생성: done
M10 MVP README 정리: done
P1 PostgreSQL 적재 확인: done
P2 FastAPI에서 PostgreSQL 조회: done
P3 MLflow 연결: done
P4 Airflow DAG scaffold/smoke: done
P5 Docker/CI 정리: done
P6 Airflow 전체 DAG E2E 실행: done
P7 포트폴리오 브리프/로컬 실행 가이드: done
Q2-1 scikit-learn baseline 교체 및 MLflow sklearn model logging: done
R1 clean clone offline sample E2E 및 CI Docker build 검증: done
R1-1 GitHub Actions 원격 green 확인: done
R2 sample PostgreSQL load 및 API smoke CI 검증: done
R3 GitHub Actions Node 24 runtime 대응: done
```

## 완료된 MLOps 포트폴리오화 작업

| ID | 작업 | 목적 | 상태 |
|---|---|---|---|
| P1 | PostgreSQL 적재 확인 | CSV 결과물을 DB 테이블로 적재 | done |
| P2 | FastAPI에서 PostgreSQL 조회 | latest risk score API | done |
| P3 | MLflow 연결 | baseline metrics/model artifact 관리 | done |
| P4 | Airflow DAG 전환 | pipeline orchestration scaffold/smoke | done |
| P5 | Docker/CI 정리 | 실행성과 자동 검증 강화 | done |
| P6 | Airflow 전체 DAG E2E 실행 | orchestration end-to-end 검증 | done |
| P7 | 포트폴리오 브리프/로컬 실행 가이드 | 공개 설명 자료와 재실행 절차 정리 | done |
| Q2-1 | scikit-learn baseline 교체 | 표준 ML workflow와 model artifact logging 확보 | done |
| R1 | clean clone offline sample E2E | 네트워크 없이 최소 sample pipeline 재현 | done |
| R1-1 | GitHub Actions 원격 green 확인 | push 후 CI 성공 여부 확인 | done |
| R2 | sample PostgreSQL/API smoke | CI에서 sample 적재와 API 조회 검증 | done |
| R3 | GitHub Actions Node 24 runtime 대응 | Node 20 deprecation warning 제거 | done |

## 다음 작업 후보

### Q1. 포트폴리오 정리

목표:

```text
채용 담당자/면접관이 빠르게 이해할 수 있는 공개용 설명 자료를 만든다.
```

작업:

```text
README 정식 개편: pending
docs/PORTFOLIO_BRIEF.md 작성: done
docs/RUNBOOK.md 작성: done
Mermaid 아키텍처 다이어그램 추가: done
실행 순서 정리: done
기술적 tradeoff 정리: done
```

### Q2. 모델 품질 개선

목표:

```text
pure Python baseline을 표준 ML workflow로 교체했고, 이제 모델 품질을 개선한다.
```

작업:

```text
scikit-learn LogisticRegression baseline: done
sklearn Pipeline + StandardScaler: done
class_weight='balanced': done
joblib artifact 저장: done
MLflow sklearn model logging: done
calibration / top-K ranking 개선: pending
tree-based model 비교: pending
```

### Q3. 데이터/label 품질 개선

목표:

```text
recall matching과 component normalization 품질을 개선한다.
```

작업:

```text
component mapping 개선
make/model alias 개선
future-dated recall handling 추가 검증
investigations/manufacturer communications 추가 검토
```

### R2. 재현성/운영성 개선

목표:

```text
clean clone과 CI에서 확인 가능한 실행 범위를 확장한다.
```

작업:

```text
clean clone에서 small sample E2E 가능하게 fixture 추가: done
CI에서 offline sample E2E 실행: done
CI에서 Docker build 검증 추가: done
sample E2E를 PostgreSQL load까지 확장: done
CI에서 docker compose up postgres/api 후 API smoke test 추가: done
collect_backfill/incremental collector Airflow DAG 분리: pending
GitHub Actions 원격 green 확인: done
GitHub Actions Node 24 runtime 대응: done
```

## 남은 주의사항

```text
1. collect_backfill은 이번 Airflow E2E DAG에 포함하지 않았다.
2. 현재 Airflow E2E는 기존 raw backfill 데이터를 기준으로 재처리한다.
3. full backfill data는 git에 포함하지 않는다.
4. clean clone용 sample E2E는 아직 Airflow/MLflow를 포함하지 않는다.
```
## R4. NHTSA scheduled collection DAG

Status: done

Implemented a separate Airflow DAG for live NHTSA snapshot collection.

```text
dag_id: nhtsa_collect_incremental
schedule: @daily
verified run_id: manual__collect_final_20260526T020000
state: success
generated collection run_id: collect_20260525T171005
vehicle count: 5
request count: 10
manifest rows: 10
```

Why this matters:

```text
The project now has a real scheduled data-collection entry point.
The current DAG collects raw JSON snapshots and validates the manifest.
It is not yet a deduplicated incremental loader.
```

Next:

```text
Make the processing DAG consume a collected run_id and trigger it after collection succeeds.
```

## R5. Collection-to-processing DAG handoff

Status: done

Implemented and verified Airflow DAG-to-DAG handoff.

```text
nhtsa_collect_incremental
  -> trigger_recall_risk_mvp
  -> nhtsa_recall_risk_mvp with dag_run.conf["run_id"]
```

Verified run:

```text
collection dag_run_id: manual__handoff_20260531T170000
generated run_id: collect_20260531T080049
processing dag_run_id: process_collect_20260531T080049
processing state: success
```

Remaining caveat after R5:

```text
Resolved by R6: load_postgres no longer truncates by default in the processing DAG.
```

## R6. PostgreSQL ingestion state and non-truncating DAG load

Status: done

Implemented first-pass incremental PostgreSQL ingestion support.

```text
ingestion_state table: done
raw_record_index table: done
load_run_id / loaded_at_utc / record_hash metadata: done
same run_id duplicate load skip: done
complaints/recalls hash dedupe: done
nhtsa_recall_risk_mvp load_postgres --truncate removal: done
```

Verified:

```text
smoke load first pass: inserted
smoke load second pass: SKIP already ingested
Airflow processing DAG without --truncate: success
full MVP restore with metadata: success
```

Next:

```text
Resolved by R7: model_version/run_id metadata is now in prediction outputs and serving views.
```

## R7. Prediction/model version metadata

Status: done

Implemented model/scoring metadata in batch outputs, PostgreSQL, and the API.

```text
latest_risk_scores:
  source_run_id
  model_version
  scoring_method
  scored_at_utc

baseline_test_predictions:
  source_run_id
  model_version
  model_type
  model_library
  scored_at_utc
```

Verified:

```text
v_latest_risk_scores model_version: rule_baseline_v1
baseline_test_predictions model_version: sklearn_logistic_v1
GET /risk-scores/latest includes model_version metadata
```

Next:

```text
Split training and batch scoring into separate steps.
```

## R8. Split training and batch scoring

Status: done

Implemented separate training and scoring entrypoints.

```text
pipelines/train_model_backfill.py
  -> sklearn_logistic_pipeline.joblib
  -> baseline_logistic_coefficients.csv
  -> baseline_training_summary.json

pipelines/score_batch_backfill.py
  -> loads sklearn_logistic_pipeline.joblib
  -> baseline_test_predictions.csv
  -> baseline_model_summary.json
```

Airflow task sequence:

```text
build_features_labels
  -> train_model
  -> score_batch
  -> generate_latest_risk_report
  -> load_postgres
  -> log_mlflow
```

Verified:

```text
dag_id: nhtsa_recall_risk_mvp
run_id: manual__train_score_split_20260601T000200
state: success
```

Next:

```text
Use MLflow model artifact/alias as the scoring input, or add a model promotion gate.
```

## R9. Model-based latest risk scoring and API

Status: done

Implemented a production-like latest-week scoring path using the trained
scikit-learn model.

```text
pipelines/score_latest_backfill.py
  -> loads sklearn_logistic_pipeline.joblib
  -> scores latest weekly_features rows
  -> model_latest_risk_scores.csv
  -> model_latest_risk_summary.json
```

PostgreSQL/API:

```text
recall_risk.model_latest_risk_scores: done
recall_risk.v_model_latest_risk_scores: done
GET /risk-scores/model/latest: done
```

Airflow task sequence:

```text
build_features_labels
  -> train_model
  -> score_batch
  -> score_latest
  -> generate_latest_risk_report
  -> load_postgres
  -> log_mlflow
```

Verified:

```text
dag_id: nhtsa_recall_risk_mvp
run_id: manual__model_latest_scoring_20260601T010000
state: success
```

Next:

```text
Use MLflow model artifact/alias as the scoring input.
Add a promotion gate before model_latest scoring is published.
```

## R10. Model promotion gate

Status: done

Implemented a model promotion gate between held-out test scoring and latest-week
model scoring.

```text
pipelines/evaluate_model_gate.py
  -> reads baseline_model_summary.json
  -> checks model artifact / predictions / test positives / AP / Brier score
  -> writes model_promotion_decision.json
  -> writes docs/MODEL_PROMOTION_GATE_RESULTS.md
```

Airflow task sequence:

```text
score_batch
  -> evaluate_model_gate
  -> score_latest
```

Current default gate:

```text
blocking:
  model artifact exists
  predictions CSV exists
  test positives >= 10
  logistic AP >= rule AP
  logistic Brier <= rule Brier

warning:
  logistic precision@25 < rule precision@25
```

Verified:

```text
source_run_id: 20260515T114046Z
promotion_status: approved
warning_count: 1
```

Next:

```text
Use MLflow model artifact/alias as the score_latest input.
Later, tighten the promotion gate with --require-precision-at-k after ranking improves.
```
