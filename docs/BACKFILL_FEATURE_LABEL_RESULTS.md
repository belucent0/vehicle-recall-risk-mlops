# Backfill Feature/Label Results

작성일: 2026-05-15 KST

## 할 작업

```text
M7. Backfill feature/label 생성
```

## 왜 하는가

M6에서 정규화한 complaints/recalls CSV를 학습 가능한 dataset으로 변환해야 한다.

## 무엇을 어떻게 했는가

라벨 로직을 보강했다.

```text
src/recall_risk/features/labels.py
```

보강 이유:

```text
recalls.csv에 현재일(2026-05-15)보다 미래인 report date가 있었다.
따라서 label_available은 max recall date가 아니라 data_as_of_date 기준으로 계산해야 한다.
```

새 파이프라인:

```text
pipelines/build_features_labels_backfill.py
```

역할:

```text
1. complaints.csv에서 weekly features 생성
2. rolling mean/std/spike score 생성
3. recalls.csv를 이용해 향후 90일 recall label 생성
4. data_as_of_date=2026-05-15 기준으로 label_available 계산
5. training_dataset.csv / training_dataset_labeled_only.csv 생성
```

## 실행 명령

```bash
python pipelines/build_features_labels_backfill.py --run-id 20260515T114046Z --data-as-of-date 2026-05-15
```

## 결과 파일

```text
data/processed/backfill/20260515T114046Z/weekly_features.csv
data/processed/backfill/20260515T114046Z/latest_risk_scores.csv
data/processed/backfill/20260515T114046Z/training_dataset.csv
data/processed/backfill/20260515T114046Z/training_dataset_labeled_only.csv
data/processed/backfill/20260515T114046Z/features_labels_summary.json
reports/backfill_features_labels_latest.md
docs/BACKFILL_FEATURE_LABEL_RESULTS.md
```

## Feature summary

| Metric | Value |
|---|---:|
| Feature rows | 1,189,569 |
| Entity count | 8,091 |
| Week count | 626 |
| Week range | 2014-05-19 ~ 2026-05-11 |
| Non-zero complaint weeks | 80,366 |

## Label summary

| Metric | Value |
|---|---:|
| Total rows | 1,189,569 |
| Label available rows | 1,172,332 |
| Label unavailable rows | 17,237 |
| Positive rows | 4,348 |
| Negative rows | 1,167,984 |
| Positive rate | 0.003709 |
| Positive entity count | 315 |
| Max as-of date | 2026-05-17 |
| Max labeled as-of date | 2026-02-08 |

## Top positive components

| Component family | Positive rows |
|---|---:|
| ELECTRICAL SYSTEM | 1037 |
| POWER TRAIN | 714 |
| SERVICE BRAKES | 498 |
| BACK OVER PREVENTION | 396 |
| STEERING | 232 |
| FUEL SYSTEM | 230 |
| SEAT BELTS | 207 |
| STRUCTURE | 201 |
| ENGINE | 186 |
| SUSPENSION | 173 |

## 알게 된 것

1. smoke test에서는 positive row가 45개였지만, MVP backfill에서는 4,348개로 늘었다.
2. 여전히 positive rate는 약 0.37%로 rare event 문제다.
3. 이제 baseline model을 다시 평가할 수 있는 규모가 되었다.
4. 90일 horizon 기준으로 2026-02-08 이후 as-of row는 label unavailable이 된다.

## 결정

M7은 완료로 본다.

다음 단계에서는 이 dataset으로 baseline model을 다시 평가한다.

## 다음 작업

```text
M8. Backfill baseline 재평가
```

주의:

```text
전체 train row가 100만 건 이상이므로, logistic baseline은 negative downsampling 또는 학습 row 제한이 필요하다.
```

