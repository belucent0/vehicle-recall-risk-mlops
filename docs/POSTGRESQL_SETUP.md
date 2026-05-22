# PostgreSQL Setup

작성일: 2026-05-16 KST

## 목적

MVP에서 생성한 CSV 결과물을 PostgreSQL에 적재한다.

PostgreSQL은 이후 다음 용도로 사용한다.

```text
1. Airflow task 결과 저장
2. FastAPI 조회용 serving store
3. feature/training/risk score 테이블 관리
4. SQL 기반 품질 점검
```

## 추가된 파일

```text
docker-compose.yml
configs/postgres.env.example
infra/postgres/initdb/001_schema.sql
pipelines/load_postgres.py
docs/POSTGRESQL_SETUP.md
```

## 실행 순서

### 1. 환경 변수 파일 준비

```bash
copy configs\postgres.env.example .env
```

PowerShell 기준:

```powershell
Copy-Item configs\postgres.env.example .env
```

### 2. PostgreSQL 실행

```bash
docker compose up -d postgres
```

기본 접속 정보:

```text
host: localhost
port: 55432
database: recall_risk
user: recall_user
password: recall_password
```

### 3. CSV 적재

```bash
python pipelines/load_postgres.py --run-id 20260515T114046Z --apply-schema --truncate
```

## 적재 대상 테이블

```text
recall_risk.backfill_manifest
recall_risk.complaints
recall_risk.recalls
recall_risk.weekly_features
recall_risk.training_dataset
recall_risk.training_dataset_labeled_only
recall_risk.latest_risk_scores
recall_risk.baseline_test_predictions
recall_risk.baseline_logistic_coefficients
```

## 조회 예시

최신 risk score:

```sql
SELECT *
FROM recall_risk.v_latest_risk_scores
ORDER BY rank
LIMIT 25;
```

positive label 수:

```sql
SELECT
  next_90d_recall,
  COUNT(*) AS rows
FROM recall_risk.v_training_dataset
WHERE label_available = 1
GROUP BY next_90d_recall
ORDER BY next_90d_recall;
```

부품군별 positive:

```sql
SELECT
  component_family,
  COUNT(*) AS positive_rows
FROM recall_risk.v_training_dataset
WHERE label_available = 1
  AND next_90d_recall = 1
GROUP BY component_family
ORDER BY positive_rows DESC
LIMIT 20;
```

## 설계 메모

현재 schema는 CSV 적재 안정성을 위해 대부분 TEXT로 저장한다.

이유:

```text
1. MVP CSV에는 빈 문자열이 많다.
2. 빠르게 적재하는 것이 우선이다.
3. typed view에서 필요한 컬럼만 casting한다.
```

나중에 운영형 schema로 바꿀 때는 다음을 고려한다.

```text
DATE / INTEGER / DOUBLE PRECISION typed tables
primary key
upsert
partitioning
data quality constraints
```

