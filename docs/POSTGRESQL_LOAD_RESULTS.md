# PostgreSQL Load Results

작성일: 2026-05-18 KST

## 목적

MVP 단계에서 생성한 CSV/JSON 산출물을 PostgreSQL에 적재해, 이후 FastAPI/MLflow/Airflow가 참조할 수 있는 운영형 저장소의 출발점을 만든다.

이번 작업은 모델 성능 개선이 아니라 **CSV 기반 실험 산출물을 DB 테이블로 옮기는 단계**다.

## 실행한 작업

### 1. PostgreSQL 컨테이너 실행

```bash
docker compose up -d postgres
```

확인 결과:

```text
container: nhtsa-recall-risk-postgres
image: postgres:16
status: healthy
port: localhost:55432 -> 5432
```

### 2. Python PostgreSQL 드라이버 설치

```bash
python -m pip install "psycopg[binary]>=3.2.0"
```

설치 결과:

```text
psycopg==3.3.4
psycopg-binary==3.3.4
```

### 3. 스키마 적용 및 MVP 결과 적재

```bash
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

적재 대상 run:

```text
20260515T114046Z
```

## 적재 결과

| table | rows |
|---|---:|
| recall_risk.backfill_manifest | 1,834 |
| recall_risk.complaints | 103,440 |
| recall_risk.recalls | 3,018 |
| recall_risk.weekly_features | 1,189,569 |
| recall_risk.training_dataset | 1,189,569 |
| recall_risk.training_dataset_labeled_only | 1,172,332 |
| recall_risk.latest_risk_scores | 25 |
| recall_risk.baseline_test_predictions | 293,083 |
| recall_risk.baseline_logistic_coefficients | 12 |

## 검증 쿼리

### 주요 테이블 row count

```sql
select table_name, row_count
from recall_risk.v_table_row_counts
order by table_name;
```

확인 결과:

```text
baseline_test_predictions | 293083
complaints                | 103440
latest_risk_scores        | 25
recalls                   | 3018
training_dataset          | 1189569
weekly_features           | 1189569
```

### 최신 risk score view

```sql
select rank, make, model, model_year, component, week_start, complaint_count, baseline_risk_score
from recall_risk.v_latest_risk_scores
order by rank
limit 5;
```

확인 결과:

| rank | make | model | model_year | component | week_start | complaint_count | score |
|---:|---|---|---:|---|---|---:|---:|
| 1 | FORD | BRONCO SPORT | 2021 | UNKNOWN OR OTHER | 2026-05-11 | 2 | 2.8062 |
| 2 | FORD | BRONCO SPORT | 2022 | ENGINE | 2026-05-11 | 1 | 2.4749 |
| 3 | FORD | ESCAPE | 2015 | POWER TRAIN | 2026-05-11 | 1 | 2.4749 |
| 4 | FORD | EXPLORER | 2020 | STRUCTURE | 2026-05-11 | 1 | 2.4749 |
| 5 | FORD | EXPLORER | 2021 | ENGINE | 2026-05-11 | 1 | 2.4749 |

## 현재 의미

완료된 것:

```text
CSV/JSON 산출물 -> PostgreSQL 테이블 적재
PostgreSQL schema 적용
기본 row count 검증
latest risk score 조회 view 검증
```

아직 안 한 것:

```text
FastAPI에서 PostgreSQL 조회
MLflow에 모델/메트릭 기록
Airflow DAG로 수집/정규화/학습 orchestration
CI에서 테스트 자동화
```

## 결론

P1 PostgreSQL 적재 확인은 완료했다.

다음 작업은 **P2 FastAPI에서 PostgreSQL을 조회하는 읽기 전용 API 구현**이다.

