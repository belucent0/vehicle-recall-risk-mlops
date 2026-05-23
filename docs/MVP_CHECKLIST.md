# MVP Checklist

목표는 완성형 MLOps 포트폴리오가 아니라 **NHTSA Recall Risk MVP**까지다.

## MVP 완료 기준

```text
1. 다수 차량 모델에 대해 NHTSA 데이터를 수집한다.
2. complaints/recalls를 정규화한다.
3. 주간 feature를 만든다.
4. 향후 90일 리콜 라벨을 만든다.
5. baseline 모델을 평가한다.
6. 최신 risk score를 CSV/리포트로 확인할 수 있다.
7. README/docs에서 재현 방법과 결과를 설명할 수 있다.
```

## Status

| ID | 작업 | 상태 | 결과 문서 |
|---|---|---|---|
| S0 | 프로젝트 폴더/구조 생성 | done | `PROJECT_STATUS.md` |
| S1 | NHTSA API smoke test | done | `SMOKE_TEST_RESULTS.md` |
| S2 | Raw JSON 정규화 | done | `NORMALIZATION_RESULTS.md` |
| S3 | Weekly feature 생성 | done | `WEEKLY_FEATURE_RESULTS.md` |
| S4 | 90일 리콜 라벨 생성 | done | `TRAINING_DATASET_RESULTS.md` |
| S5 | Baseline model 평가 | done | `BASELINE_MODEL_RESULTS.md` |
| M1 | VPIC vehicle model list 수집 | done | `VEHICLE_MODELS_RESULTS.md` |
| M2 | 모델명 alias/정규화 | done | `MODEL_ALIAS_RESULTS.md` |
| M3 | Backfill collector 구현 | done | `BACKFILL_COLLECTION_RESULTS.md` |
| M4 | Backfill 대상 vehicle model 후보 정제 | done | `VEHICLE_MODEL_FILTER_RESULTS.md` |
| M5 | MVP 후보 vehicle backfill 수집 실행 | done | `BACKFILL_COLLECTION_RESULTS.md` |
| M6 | Backfill 정규화 | done | `BACKFILL_NORMALIZATION_RESULTS.md` |
| M7 | Backfill feature/label 생성 | done | `BACKFILL_FEATURE_LABEL_RESULTS.md` |
| M8 | Backfill baseline 재평가 | done | `BACKFILL_BASELINE_MODEL_RESULTS.md` |
| M9 | 최신 risk score 리포트 생성 | done | `LATEST_RISK_SCORE_RESULTS.md` |
| M10 | MVP README 정리 | done | `MVP_SUMMARY.md` |

## 완료된 작업: M4

### 할 작업

```text
Backfill 대상 vehicle model 후보를 정제한다.
```

### 왜 하는가

VPIC model list에 일반 차량 모델이 아닌 노이즈가 포함되어 있음을 확인했다.

MVP에서는 전체 VPIC 목록을 그대로 쓰기보다 대표 차량 모델 중심의 후보 CSV를 만들어야 한다.

### 만든 파일

```text
pipelines/filter_vehicle_models_mvp.py
docs/VEHICLE_MODEL_FILTER_RESULTS.md
```

### 실행

```bash
python pipelines/filter_vehicle_models_mvp.py
```

### 결과

```text
data/interim/vehicle_models_mvp.csv
data/interim/vehicle_models_excluded.csv
reports/vehicle_model_filter_latest.md
docs/VEHICLE_MODEL_FILTER_RESULTS.md
```

요약:

```text
input rows: 1301
included rows: 1012
excluded rows: 289
```

포함:

```text
FORD: 409
HYUNDAI: 162
KIA: 136
TESLA: 43
TOYOTA: 262
```

### 성공 기준 체크

```text
1. vehicle_models.csv에서 명백한 노이즈 모델을 제외한다. done
2. 제조사/연식별 후보 수를 리포트로 확인한다. done
3. 다음 backfill 실행에서 사용할 입력 CSV를 만든다. done
```

## 완료된 작업: M5

### 할 작업

```text
MVP 후보 vehicle backfill 수집을 실행한다.
```

### 왜 하는가

`vehicle_models_mvp.csv`를 만들었으므로 이제 이 후보 목록에 대해 complaints/recalls raw JSON을 실제로 수집해야 한다.

### 실행

```bash
python pipelines/collect_backfill.py --vehicle-models data/interim/vehicle_models_mvp.csv --limit 0
```

summary 작성 오류가 있어 raw JSON에서 manifest를 복구했다.

```bash
python pipelines/recover_backfill_manifest.py --run-id 20260515T114046Z
```

### 결과

```text
data/raw/backfill/20260515T114046Z/
data/raw/backfill/20260515T114046Z/manifest.csv
docs/BACKFILL_COLLECTION_RESULTS.md
```

요약:

```text
unique vehicle-year count: 917
request count: 1834
complaints total records: 103440
recalls total records: 3018
```

### 성공 기준 체크

```text
1. vehicle_models_mvp.csv의 unique vehicle-year를 순회한다. done
2. complaints/recalls raw JSON을 저장한다. done
3. manifest.csv에 count/status를 기록한다. done
4. 수집 요약 리포트를 생성한다. done
```

## 완료된 작업: M6

### 할 작업

```text
Backfill raw JSON을 정규화한다.
```

### 왜 하는가

M5에서 raw JSON은 수집했지만 아직 분석 가능한 CSV가 아니다.

### 만들 파일

```text
pipelines/normalize_backfill.py
docs/BACKFILL_NORMALIZATION_RESULTS.md
```

### 출력 파일

```text
data/interim/backfill/20260515T114046Z/complaints.csv
data/interim/backfill/20260515T114046Z/recalls.csv
reports/backfill_normalization_latest.md
```

### 결과

```text
complaints rows: 103440
recalls rows: 3018
complaints date range: 2014-05-21 ~ 2026-05-13
recalls date range: 2014-05-11 ~ 2026-10-04
```

### 성공 기준 체크

```text
1. complaints 103,440건이 정규화된다. done
2. recalls 3,018건이 정규화된다. done
3. 날짜/component/make/model 필드가 CSV로 저장된다. done
4. row count/date range/component summary가 문서화된다. done
```

## 완료된 작업: M7

### 할 작업

```text
Backfill feature/label을 생성한다.
```

### 왜 하는가

정규화된 complaints/recalls CSV를 학습 가능한 dataset으로 변환해야 한다.

### 출력

```text
data/processed/backfill/20260515T114046Z/weekly_features.csv
data/processed/backfill/20260515T114046Z/training_dataset.csv
reports/backfill_features_labels_latest.md
```

### 결과

```text
feature rows: 1189569
entity count: 8091
label available rows: 1172332
positive rows: 4348
positive rate: 0.003709
```

### 성공 기준 체크

```text
1. weekly feature rows가 생성된다. done
2. 90일 recall label이 생성된다. done
3. data_as_of_date=2026-05-15 기준으로 label_available을 계산한다. done
4. positive rate와 label 분포가 문서화된다. done
```

## 완료된 작업: M8

### 할 작업

```text
Backfill dataset으로 baseline model을 재평가한다.
```

### 왜 하는가

smoke test 모델 평가는 positive가 너무 적어서 의미가 약했다. 이제 positive row가 4,348개 있으므로 더 의미 있는 평가가 가능하다.

### 출력

```text
data/processed/backfill/20260515T114046Z/baseline_test_predictions.csv
data/processed/backfill/20260515T114046Z/baseline_model_summary.json
reports/backfill_baseline_model_latest.md
```

### 결과

```text
train rows: 879249
train positives: 2737
test rows: 293083
test positives: 1611
rule AP: 0.006281
logistic AP: 0.008191
```

### 성공 기준 체크

```text
1. 시간 기준 train/test split을 한다. done
2. rule baseline을 평가한다. done
3. downsampled logistic baseline을 평가한다. done
4. Precision@K, Average Precision, positive rate를 문서화한다. done
```

## 완료된 작업: M9

### 할 작업

```text
최신 risk score 리포트를 생성한다.
```

### 왜 하는가

MVP 최종 산출물에는 "현재 어떤 차량/부품 조합이 위험 신호가 높은가"를 보여주는 결과물이 필요하다.

### 출력

```text
reports/latest_risk_score_report.md
docs/LATEST_RISK_SCORE_RESULTS.md
```

### 결과

```text
latest week: 2026-05-11
top-k rows: 25
top score: 2.8062
```

### 성공 기준 체크

```text
1. latest_risk_scores.csv를 읽는다. done
2. top risk vehicle/component를 markdown으로 정리한다. done
3. score 해석과 한계를 문서화한다. done
```

## 완료된 작업: M10

### 할 작업

```text
MVP README를 정리한다.
```

### 왜 하는가

지금까지 단계별 파일은 많지만, 포트폴리오/재현 관점에서 프로젝트의 목적, 실행 순서, 결과, 한계를 한 곳에서 볼 수 있어야 한다.

### 출력

```text
README.md
docs/MVP_SUMMARY.md
```

### 성공 기준 체크

```text
1. MVP 범위가 명확히 설명된다. done
2. end-to-end 실행 순서가 정리된다. done
3. 주요 결과 수치가 들어간다. done
4. 한계와 다음 확장 방향이 들어간다. done
```

## MVP 상태

```text
MVP complete
```
