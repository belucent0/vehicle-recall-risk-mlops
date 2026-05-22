# VPIC Vehicle Model List Results

- Built at UTC: `2026-05-14T16:42:00.061985+00:00`
- Output CSV: `data\interim\vehicle_models.csv`
- Total rows: `1301`

## Counts by Make

| Make | Rows | Unique normalized models |
|---|---:|---:|
| FORD | 615 | 54 |
| HYUNDAI | 190 | 30 |
| KIA | 152 | 22 |
| TESLA | 46 | 6 |
| TOYOTA | 298 | 42 |

## Counts by Year

| Year | Rows |
|---:|---:|
| 2015 | 92 |
| 2016 | 94 |
| 2017 | 99 |
| 2018 | 101 |
| 2019 | 103 |
| 2020 | 108 |
| 2021 | 107 |
| 2022 | 113 |
| 2023 | 117 |
| 2024 | 118 |
| 2025 | 123 |
| 2026 | 126 |

## FORD F-150-like Model Names

| Year | Make Name | Model Name | Normalized | Model ID |
|---:|---|---|---|---:|
| 2015 | FORD | F-150 | F 150 | 1801 |
| 2016 | FORD | F-150 | F 150 | 1801 |
| 2017 | FORD | F-150 | F 150 | 1801 |
| 2018 | FORD | F-150 | F 150 | 1801 |
| 2019 | FORD | F-150 | F 150 | 1801 |
| 2020 | FORD | F-150 | F 150 | 1801 |
| 2021 | FORD | F-150 | F 150 | 1801 |
| 2022 | FORD | F-150 | F 150 | 1801 |
| 2023 | FORD | F-150 | F 150 | 1801 |
| 2024 | FORD | F-150 | F 150 | 1801 |
| 2025 | FORD | F-150 | F 150 | 1801 |
| 2026 | FORD | F-150 | F 150 | 1801 |

## Interpretation

- 이 결과는 backfill collector가 순회할 제조사/연식/모델 후보 목록이다.
- 같은 모델도 연식별로 반복되므로 row 수는 unique model 수보다 크다.
- 다음 단계에서는 이 목록을 NHTSA complaints/recalls endpoint에 넣어 실제 수집 성공률을 확인한다.
- FORD F-150처럼 API endpoint별 모델명 표기가 달라질 수 있으므로 alias 정규화가 필요하다.