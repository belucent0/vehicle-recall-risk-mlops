# Backfill Baseline Model Results

작성일: 2026-05-15 KST

## 할 작업

```text
M8. Backfill baseline 재평가
```

## 왜 하는가

smoke test에서는 positive row가 45개뿐이라 모델 평가가 거의 의미 없었다. M7에서 positive row가 4,348개로 늘었으므로 MVP dataset 기준으로 baseline을 다시 평가한다.

## 무엇을 어떻게 했는가

다음 스크립트를 만들었다.

```text
pipelines/train_baseline_backfill.py
```

평가 방식:

```text
1. training_dataset_labeled_only.csv 로드
2. 시간 기준 train/test split
3. rule baseline 평가: baseline_risk_score
4. logistic baseline 평가: positive 전체 + negative downsampling
5. Precision@K, Average Precision, Brier score 계산
```

전체 train row가 많기 때문에 logistic은 모든 negative를 쓰지 않았다.

```text
negative_ratio=20
max_train_rows=100000
actual logistic train sample rows=57477
```

## 실행 명령

```bash
python pipelines/train_baseline_backfill.py --run-id 20260515T114046Z --epochs 120 --negative-ratio 20 --max-train-rows 100000
```

## 결과 파일

```text
data/processed/backfill/20260515T114046Z/baseline_test_predictions.csv
data/processed/backfill/20260515T114046Z/baseline_logistic_coefficients.csv
data/processed/backfill/20260515T114046Z/baseline_model_summary.json
reports/backfill_baseline_model_latest.md
docs/BACKFILL_BASELINE_MODEL_RESULTS.md
```

## Split

Split cutoff:

```text
2024-04-21
```

| Split | Rows | Positives | Positive rate | Date range |
|---|---:|---:|---:|---|
| train | 879249 | 2737 | 0.003113 | 2014-05-25 ~ 2024-04-21 |
| test | 293083 | 1611 | 0.005497 | 2024-04-21 ~ 2026-02-08 |

## Test metrics

### Rule baseline

| Metric | Value |
|---|---:|
| Average precision | 0.006281 |
| Brier score | 0.240245 |
| Precision@25 | 0.08 |
| Recall@25 | 0.001241 |
| Precision@50 | 0.08 |
| Recall@50 | 0.002483 |
| Precision@100 | 0.04 |
| Recall@100 | 0.002483 |

### Logistic baseline

| Metric | Value |
|---|---:|
| Average precision | 0.008251 |
| Brier score | 0.103041 |
| Precision@25 | 0.0 |
| Precision@50 | 0.0 |
| Precision@100 | 0.0 |

## 해석

1. Logistic의 Average Precision은 rule baseline보다 약간 높다.
2. 하지만 Top-K에서는 logistic이 좋지 않다. 상위 score가 false positive에 몰렸다.
3. Logistic score가 1.0으로 포화되는 케이스가 있어 calibration이 좋지 않다.
4. 현재 모델은 "최종 모델"이 아니라 MVP baseline이다.
5. 그래도 smoke test보다 훨씬 의미 있는 평가가 가능해졌다.

## 결정

M8은 완료로 본다.

다음 단계에서는 최신 week 기준 risk score 리포트를 MVP 산출물로 정리한다.

## 다음 작업

```text
M9. 최신 risk score 리포트 생성
```

목표:

```text
latest_risk_scores.csv를 사람이 읽을 수 있는 markdown report로 정리한다.
```

