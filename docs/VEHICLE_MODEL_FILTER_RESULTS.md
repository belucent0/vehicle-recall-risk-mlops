# Vehicle Model Filter Results

작성일: 2026-05-15 KST

## 할 작업

```text
M4. Backfill 대상 vehicle model 후보 정제
```

## 왜 하는가

M3 제한 backfill에서 VPIC 모델 리스트에 일반 차량 모델이 아닌 노이즈가 포함되어 있음을 확인했다.

예:

```text
AFFORDABLE ALUMINUM
BRADFORD BUILT
CRANFORD RADIATOR INC.
EAGLE FORD TANKS & TRAILERS LLC
FORDS TRAILER SALES
MEDFORD STEEL
MILFORD PIPE & SUPPLY
```

전체 `vehicle_models.csv`를 그대로 backfill하면 불필요한 empty 요청이 많아진다. 따라서 MVP에서는 대표 차량 모델 whitelist를 사용해 수집 후보를 정제한다.

## 무엇을 어떻게 했는가

다음 스크립트를 만들었다.

```text
pipelines/filter_vehicle_models_mvp.py
```

역할:

```text
1. data/interim/vehicle_models.csv 읽기
2. 제조사별 MVP whitelist와 비교
3. 포함 후보는 vehicle_models_mvp.csv로 저장
4. 제외 후보는 vehicle_models_excluded.csv로 저장
5. 제조사/연식별 포함 수와 제외 샘플을 리포트로 저장
```

## 실행 명령

```bash
python pipelines/filter_vehicle_models_mvp.py
```

## 결과 파일

```text
data/interim/vehicle_models_mvp.csv
data/interim/vehicle_models_excluded.csv
data/interim/vehicle_model_filter_summary.json
reports/vehicle_model_filter_latest.md
docs/VEHICLE_MODEL_FILTER_RESULTS.md
```

## 결과 요약

| Metric | Value |
|---|---:|
| Input rows | 1301 |
| Included rows | 1012 |
| Excluded rows | 289 |

## Included by Make

| Make | Rows | Unique included models |
|---|---:|---:|
| FORD | 409 | 35 |
| HYUNDAI | 162 | 27 |
| KIA | 136 | 20 |
| TESLA | 43 | 5 |
| TOYOTA | 262 | 39 |

## Included by Year

| Year | Rows |
|---:|---:|
| 2015 | 73 |
| 2016 | 75 |
| 2017 | 76 |
| 2018 | 78 |
| 2019 | 79 |
| 2020 | 84 |
| 2021 | 83 |
| 2022 | 89 |
| 2023 | 90 |
| 2024 | 91 |
| 2025 | 95 |
| 2026 | 99 |

## 제외 결과

| Reason | Rows |
|---|---:|
| model_not_in_mvp_whitelist | 289 |

제외 샘플:

```text
FORD '34
FORD AFFORDABLE ALUMINUM
FORD BRADFORD BUILT
FORD COMMERCIAL CHASSIS
FORD CRANFORD RADIATOR INC.
FORD EAGLE FORD TANKS & TRAILERS LLC
FORD FORDS TRAILER SALES
FORD MEDFORD STEEL
FORD MILFORD PIPE & SUPPLY
FORD MOTORHOME CHASSIS
```

## 알게 된 것

1. VPIC 전체 모델 리스트는 수집 후보로 바로 쓰기에는 노이즈가 있다.
2. whitelist 기반 1차 필터로 1301개 row를 1012개로 줄였다.
3. MVP 범위에서는 1012개 vehicle-year도 충분히 크다.
4. 다음 backfill은 `vehicle_models_mvp.csv`를 입력으로 실행한다.

## 결정

M4는 완료로 본다.

다음 단계에서는 `vehicle_models_mvp.csv`를 사용해 MVP용 backfill 수집을 실행한다.

## 다음 작업

```text
M5. MVP 후보 vehicle backfill 수집 실행
```

예상 명령:

```bash
python pipelines/collect_backfill.py --vehicle-models data/interim/vehicle_models_mvp.csv --limit 0
```

주의:

```text
1012개 vehicle-year * 2 endpoints = 2024 requests
```

