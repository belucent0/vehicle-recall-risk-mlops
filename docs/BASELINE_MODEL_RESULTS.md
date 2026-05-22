# Baseline Model Results

## Run: 2026-05-14 UTC

실행 명령:

```bash
python pipelines/train_baseline_sample.py
```

입력:

```text
data/processed/smoke_test/20260514T154719Z/training_dataset_labeled_only.csv
```

출력:

```text
data/processed/smoke_test/20260514T154719Z/baseline_predictions.csv
data/processed/smoke_test/20260514T154719Z/baseline_logistic_coefficients.csv
data/processed/smoke_test/20260514T154719Z/baseline_model_summary.json
reports/baseline_model_latest.md
```

## Split

시간 기준 split을 사용했다.

| Split | Rows | Positives | Positive rate |
|---|---:|---:|---:|
| train | 5765 | 41 | 0.007112 |
| test | 4695 | 4 | 0.000852 |

Split cutoff:

```text
as_of_date <= 2024-04-07 -> train
as_of_date > 2024-04-07  -> test
```

## Test Metrics

### Rule baseline

`baseline_risk_score`를 그대로 ranking score로 사용했다.

| Metric | Value |
|---|---:|
| Average precision | 0.008073 |
| Brier score | 0.19084 |
| Precision@100 | 0.0 |
| Recall@100 | 0.0 |

### Logistic baseline

Pure-Python weighted logistic regression을 사용했다. 외부 ML dependency 없이 smoke test용으로 구현했다.

| Metric | Value |
|---|---:|
| Average precision | 0.001549 |
| Brier score | 0.169114 |
| Precision@100 | 0.0 |
| Recall@100 | 0.0 |

## Interpretation

현재 모델 성능은 좋지 않다. 하지만 이 단계에서는 정상이다.

이유:

1. smoke-test 대상 차량이 5개뿐이다.
2. label-ready test positive가 4개뿐이다.
3. NHTSA recall은 매우 희귀한 이벤트다.
4. complaint component와 recall component를 아직 거칠게 매칭한다.
5. investigations/manufacturer communications 같은 강한 전조 신호를 아직 쓰지 않았다.

## Decision

다음 단계에서 모델 튜닝을 하는 것은 비효율적이다.

먼저 해야 할 일:

1. 데이터 범위를 넓힌다.
2. VPIC 기반 make/model 정규화를 강화한다.
3. NHTSA 전체 또는 다수 모델에 대해 backfill한다.
4. positive sample을 늘린 뒤 모델을 다시 평가한다.

