# Weekly Feature Results

## Run: 2026-05-14 UTC

실행 명령:

```bash
python pipelines/build_features_sample.py
```

입력:

```text
data/interim/smoke_test/20260514T154719Z/complaints.csv
```

출력:

```text
data/processed/smoke_test/20260514T154719Z/weekly_features.csv
data/processed/smoke_test/20260514T154719Z/latest_risk_scores.csv
reports/weekly_features_latest.md
```

## Summary

| Metric | Value |
|---|---:|
| Feature rows | 10725 |
| Entity count | 84 |
| Week range | 2021-07-12 ~ 2026-05-11 |
| Non-zero complaint weeks | 960 |

## Current CSV Tables

현재 MVP에서는 DBMS 테이블이 아니라 CSV 기반의 tabular dataset을 사용한다.

```text
raw JSON
  -> normalized CSV
  -> feature CSV
  -> score CSV
```

나중에 같은 스키마를 DuckDB/Postgres 테이블로 옮기면 된다.

## Latest Week Top Risk Scores

| Rank | Make | Model | Year | Component | Week | Complaints | Severe | Spike Z | Score |
|---:|---|---|---:|---|---:|---:|---:|---:|---:|
| 1 | TOYOTA | RAV4 | 2022 | ELECTRICAL SYSTEM | 2026-05-11 | 1 | 0 | 0.4677 | 0.4677 |
| 2 | TESLA | MODEL 3 | 2022 | VEHICLE SPEED CONTROL | 2026-05-11 | 1 | 0 | 0.0 | 0.0 |
| 3 | TOYOTA | RAV4 | 2022 | LATCHES/LOCKS/LINKAGES | 2026-05-11 | 1 | 0 | 0.0 | 0.0 |

## Interpretation

아직 샘플 데이터가 작고 latest week 기준이라 risk score가 거의 낮다.

다음 단계에서는 특정 과거 시점을 잡고, 그 시점 이후 90일 내 리콜 발생 여부를 붙이는 label table을 만들어야 한다.

