# Backfill Normalization Results

작성일: 2026-05-15 KST

## 할 작업

```text
M6. Backfill 정규화
```

## 왜 하는가

M5에서 raw JSON은 수집했지만 아직 분석 가능한 형태가 아니다. 모델링과 feature 생성을 위해 complaints/recalls를 CSV로 정규화해야 한다.

## 무엇을 어떻게 했는가

다음 스크립트를 만들었다.

```text
pipelines/normalize_backfill.py
```

역할:

```text
1. data/raw/backfill/<run_id>의 complaints/recalls JSON 읽기
2. 기존 normalize_complaint/normalize_recall 로직 재사용
3. complaints.csv / recalls.csv 생성
4. row count, date range, top components 리포트 생성
```

## 실행 명령

```bash
python pipelines/normalize_backfill.py --run-id 20260515T114046Z
```

## 결과 파일

```text
data/interim/backfill/20260515T114046Z/complaints.csv
data/interim/backfill/20260515T114046Z/recalls.csv
data/interim/backfill/20260515T114046Z/summary.json
reports/backfill_normalization_latest.md
docs/BACKFILL_NORMALIZATION_RESULTS.md
```

## 결과 요약

| Table | Rows | Min Date | Max Date |
|---|---:|---:|---:|
| complaints | 103440 | 2014-05-21 | 2026-05-13 |
| recalls | 3018 | 2014-05-11 | 2026-10-04 |

## Top complaint components

| Component | Count |
|---|---:|
| ENGINE | 18957 |
| POWER TRAIN | 15928 |
| UNKNOWN OR OTHER | 11310 |
| ELECTRICAL SYSTEM | 11050 |
| STRUCTURE | 6200 |
| STEERING | 5722 |
| SERVICE BRAKES | 5255 |
| ENGINE AND ENGINE COOLING | 4413 |
| AIR BAGS | 3370 |
| VEHICLE SPEED CONTROL | 2673 |

## Top recall components

| Component | Count |
|---|---:|
| FUEL SYSTEM | 204 |
| SERVICE BRAKES | 155 |
| BACK OVER PREVENTION:SOFTWARE | 138 |
| EQUIPMENT:OTHER:LABELS | 136 |
| ELECTRICAL SYSTEM: INSTRUMENT CLUSTER/PANEL | 115 |
| BACK OVER PREVENTION: SENSING SYSTEM: CAMERA | 96 |
| ENGINE | 77 |
| ELECTRICAL SYSTEM:SOFTWARE | 62 |
| SEATS | 56 |
| ELECTRICAL SYSTEM:ADAS:AUTONOMOUS/SELF DRIVING:SOFTWARE | 51 |

## 알게 된 것

1. MVP backfill 데이터는 smoke test보다 훨씬 크다.
2. complaints 103,440건과 recalls 3,018건이 정규화되었다.
3. 주요 complaint component는 ENGINE, POWER TRAIN, ELECTRICAL SYSTEM 등이다.
4. recall date max가 2026-10-04로 현재일(2026-05-15)보다 미래인 값이 있다. label 생성 시 현재 기준 data cutoff를 명시해야 한다.

## 결정

M6는 완료로 본다.

다음 단계에서는 이 CSV를 사용해 weekly features와 90일 recall labels를 생성한다.

## 다음 작업

```text
M7. Backfill feature/label 생성
```

주의:

```text
label_available 기준은 단순 max recall date가 아니라 data_as_of_date=2026-05-15 기준으로 잡는다.
```

