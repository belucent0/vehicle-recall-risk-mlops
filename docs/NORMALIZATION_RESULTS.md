# Normalization Results

## Run: 2026-05-14 UTC

실행 명령:

```bash
python pipelines/normalize_sample.py
```

입력:

```text
data/raw/smoke_test/20260514T154719Z/
```

출력:

```text
data/interim/smoke_test/20260514T154719Z/complaints.csv
data/interim/smoke_test/20260514T154719Z/recalls.csv
reports/normalized_sample_latest.md
```

## Row Counts

| Table | Rows | Min Date | Max Date |
|---|---:|---:|---:|
| complaints | 1334 | 2021-07-14 | 2026-05-12 |
| recalls | 51 | 2021-09-07 | 2026-05-05 |

## Top Complaint Components

| Component | Count |
|---|---:|
| FORWARD COLLISION AVOIDANCE | 284 |
| UNKNOWN OR OTHER | 180 |
| VEHICLE SPEED CONTROL | 170 |
| ELECTRICAL SYSTEM | 131 |
| SERVICE BRAKES | 109 |
| POWER TRAIN | 87 |
| VISIBILITY/WIPER | 76 |
| STEERING | 55 |
| ENGINE | 43 |
| STRUCTURE | 36 |

## Top Recall Components

| Component | Count |
|---|---:|
| EXTERIOR LIGHTING:LIGHTING CONTROL MODULE | 5 |
| ELECTRICAL SYSTEM: INSTRUMENT CLUSTER/PANEL | 4 |
| ELECTRICAL SYSTEM:SOFTWARE | 4 |
| POWER TRAIN:DRIVELINE:DRIVESHAFT | 3 |
| ELECTRICAL SYSTEM: INTEGRATED TRAILER BRAKE CONTROL | 3 |
| POWER TRAIN:AUTOMATIC TRANSMISSION | 2 |
| BACK OVER PREVENTION:SOFTWARE | 2 |
| FUEL SYSTEM | 2 |
| TRAILER HITCHES | 2 |
| ELECTRICAL SYSTEM:ADAS:AUTONOMOUS/SELF DRIVING:SOFTWARE | 2 |

## Next Issue

complaints와 recalls의 component taxonomy가 완전히 일치하지 않는다.

예:

- complaints: `ELECTRICAL SYSTEM`
- recalls: `ELECTRICAL SYSTEM:SOFTWARE`

따라서 1차 MVP에서는 `component_primary`를 기준으로 거칠게 매칭하고, 이후 더 정교한 component mapping을 만든다.

