# Training Dataset Results

## Run: 2026-05-14 UTC

실행 명령:

```bash
python pipelines/build_training_dataset_sample.py
```

입력:

```text
data/processed/smoke_test/20260514T154719Z/weekly_features.csv
data/interim/smoke_test/20260514T154719Z/recalls.csv
```

출력:

```text
data/processed/smoke_test/20260514T154719Z/training_dataset.csv
data/processed/smoke_test/20260514T154719Z/training_dataset_labeled_only.csv
reports/training_dataset_latest.md
```

## Label Definition

각 row는 다음 단위를 의미한다.

```text
make / model / model_year / component_family / week
```

라벨은 다음과 같다.

```text
next_90d_recall = as_of_date 이후 90일 안에 같은 차량/부품군 리콜이 발생했는가
```

`as_of_date`는 해당 주의 마지막 날로 잡는다.

```text
as_of_date = week_start + 6 days
```

너무 최근 row는 아직 90일 후 결과를 모른다. 그런 row는 다음처럼 처리한다.

```text
label_available = 0
```

## Label Summary

| Metric | Value |
|---|---:|
| Total rows | 10725 |
| Label available rows | 10460 |
| Label unavailable rows | 265 |
| Positive rows | 45 |
| Negative rows | 10415 |
| Positive rate | 0.004302 |
| Positive entity count | 2 |
| Max as-of date | 2026-05-17 |
| Max labeled as-of date | 2026-02-01 |

## Top Positive Components

| Component family | Positive rows |
|---|---:|
| ELECTRICAL SYSTEM | 32 |
| SEATS | 13 |

## Interpretation

샘플 데이터만 사용했기 때문에 positive row가 매우 적다.

이건 실패가 아니라 예상된 결과다. 리콜은 희귀 이벤트이므로 전체 backfill을 하기 전까지는 다음을 목표로 한다.

1. 라벨 생성 로직이 동작하는지 확인
2. 데이터 누수를 막는 `as_of_date` 구조를 만든다
3. class imbalance를 확인한다
4. 이후 backfill로 positive sample을 늘린다

현재 positive rate는 약 0.43%다. 따라서 첫 모델 평가는 accuracy가 아니라 다음 중심으로 해야 한다.

- Precision@K
- PR-AUC
- Recall@K
- calibration
- early-warning lead time

