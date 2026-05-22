# Tech Stack Decision

작성일: 2026-05-16 KST

## 결정

```text
DuckDB는 도입하지 않고 PostgreSQL을 메인 저장소로 사용한다.
```

## 이유

사용자는 백엔드 개발자이고 PostgreSQL, Airflow, MLflow, FastAPI, Docker, CI에 익숙하다.

따라서 포트폴리오 관점에서는 다음 구조가 더 자연스럽다.

```text
NHTSA API
  -> Airflow pipeline
  -> PostgreSQL
  -> MLflow
  -> FastAPI
  -> CI/Docker
```

## PostgreSQL의 역할

이 프로젝트에서 PostgreSQL은 다음 역할을 맡는다.

```text
1. 정규화된 complaints/recalls 저장
2. weekly_features 저장
3. training_dataset 저장
4. latest_risk_scores 저장
5. baseline predictions 저장
6. FastAPI 조회용 serving store 역할
```

## DuckDB를 쓰지 않는 이유

DuckDB는 CSV/Parquet 분석에는 좋지만, 이번 프로젝트에서는 다음 이유로 우선순위에서 제외한다.

```text
1. 사용자가 PostgreSQL에 더 익숙하다.
2. FastAPI와 연결하기 PostgreSQL이 더 자연스럽다.
3. Airflow task 간 상태/결과 저장에도 PostgreSQL이 익숙하다.
4. 백엔드 -> MLOps 전환 포트폴리오에서 PostgreSQL은 설명하기 쉽다.
```

## 현재 도입 범위

이번 단계에서는 PostgreSQL을 "기술스택 도입 1단계"로만 붙인다.

하는 것:

```text
1. docker-compose.yml 추가
2. PostgreSQL schema 추가
3. CSV 결과물을 PostgreSQL에 적재하는 스크립트 추가
```

아직 하지 않는 것:

```text
1. Airflow DAG 전환
2. MLflow tracking server 연동
3. FastAPI에서 PostgreSQL 조회
4. CI 구성
```

이후 순서:

```text
PostgreSQL 적재
  -> FastAPI 조회
  -> MLflow
  -> Airflow
  -> Docker/CI 정리
```

